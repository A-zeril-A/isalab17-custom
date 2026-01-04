from odoo import models, fields, api
from datetime import datetime, time, timedelta
import requests
import io
import base64
import xlsxwriter
import xml.etree.ElementTree as ET
from odoo import http
from odoo.http import content_disposition, request

class TimesheetReport(models.Model):
    _name = 'timesheet.report'
    _description = 'Timesheet Report'
    _auto = False  # مدل بدون جدول پایگاه داده، فقط برای گزارش

    employee_id = fields.Many2one('hr.employee', string='Employee')
    date = fields.Date(string='Date')
    date_time = fields.Datetime(string="Start Time", store=True)
    end_time = fields.Datetime(string='End Time', store=True)
    total_hours = fields.Float(string='Total Hours')
    project_id = fields.Many2one('project.project', string='Project')
    task_id = fields.Many2one('project.task', string='Task')
    hours_18_22 = fields.Float(string="Hours 18-22")
    hours_22_06 = fields.Float(string="Hours 22-06")
    is_holiday = fields.Boolean(string="Is Holiday", compute="_compute_is_holiday")
    
    # TIME OFF
    leave_type = fields.Char(string='Leave Type')
    
    # فیلدهای جدید برای محاسبه تأخیر
    delay_hours = fields.Float(string='Delay Hours', store=True)
    delay_minutes = fields.Integer(string='Delay Minutes', store=True)
    is_delayed = fields.Boolean(string='Is Delayed', store=True)
    delay_display = fields.Char(string='Delay Time', store=True)

    day_of_week = fields.Char(string='Day of Week',compute='_compute_day_of_week',store=True,)

    colored_day_display = fields.Html(
        string='Day of Week',
        compute='_compute_day_info',
        sanitize=False
    )

    office_hours = fields.Float(
        string='Office Hours (8:30-18:30)',
        compute='_compute_office_hours',
        help='ساعت کاری در بازه زمانی اداری با محاسبه دقیق'
    )

    colored_delay_display = fields.Html(string="Delay (Colored)", compute="_compute_colored_delay_display", sanitize=False)

    hours_shortage = fields.Float(
        string='Hours Shortage', 
        compute='_compute_hours_shortage',
        help='مقدار ساعت کم کاری نسبت به ۸ ساعت استاندارد'
    )
    is_short_hours = fields.Boolean(
        string='Less Than 8 Hours', 
        compute='_compute_hours_shortage',
        help='آیا کمتر از ۸ ساعت کار کرده است؟'
    )

    _italy_holidays_cache = {}

    def _format_hours(self, hours_float):
        """تبدیل float به متن h m"""
        if hours_float is None:
            return "00:00"
        try:
            hours = int(hours_float)
            minutes = int(round((hours_float - hours) * 60))
            return f"{hours:02d}:{minutes:02d}"
        except (TypeError, ValueError):
            return "00:00"


    @classmethod
    def get_italy_holidays(cls, year):
        """کش ساده برای جلوگیری از چند بار درخواست API"""
        if not hasattr(cls, "_italy_holidays_cache"):
            cls._italy_holidays_cache = {}

        if year not in cls._italy_holidays_cache:
            try:
                url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/IT"
                response = requests.get(url, timeout=5)
                holidays = set()
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        holidays.add(item["date"])
                cls._italy_holidays_cache[year] = holidays
            except:
                cls._italy_holidays_cache[year] = set()

        return cls._italy_holidays_cache[year]

    @api.depends('date')
    def _compute_is_holiday(self):
        for rec in self:
            if not rec.date:
                rec.is_holiday = False
                continue

            year = rec.date.year
            holidays = self.get_italy_holidays(year)
            weekday = rec.date.weekday()  # 0=Mon ... 6=Sun
            date_str = rec.date.strftime("%Y-%m-%d")
            x = rec.date.strftime("%Y-%m-%d")

            rec.is_holiday = (weekday in (5, 6)) or (x in holidays)

    @api.depends('date', 'is_holiday')
    def _compute_day_info(self):
        for rec in self:
            if not rec.date:
                rec.colored_day_display = ""
                continue

            day_name = rec.date.strftime("%A")

            if rec.is_holiday:
                rec.colored_day_display = f"""
                    <span style="
                        background-color: #ffdddd;
                        color: #a00;
                        padding: 3px 8px;
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 13px;
                        display: inline-block;
                        text-align: center;
                        min-width: 80px;">
                        {day_name}
                    </span>
                """
            else:
                rec.colored_day_display = f"""
                    <span style="
                        background-color: #ddffdd;
                        color: #060;
                        padding: 3px 8px;
                        border-radius: 8px;
                        font-weight: bold;
                        font-size: 13px;
                        display: inline-block;
                        text-align: center;
                        min-width: 80px;">
                        {day_name}
                    </span>
                """

    @api.depends('delay_display', 'is_delayed')
    def _compute_colored_delay_display(self):
        for record in self:
            if record.is_delayed:
                color = "#ffdddd"
                text_color = "#a00"
            else:
                color = "#ddffdd"
                text_color = "#060"
            record.colored_delay_display = f"""
                <span style="
                    background-color: {color};
                    color: {text_color};
                    padding: 3px 8px;
                    border-radius: 8px;
                    font-weight: bold;
                    font-size: 13px;
                    display: inline-block;
                    text-align: center;
                    min-width: 80px;">
                    {record.delay_display}
                </span>
            """

    @api.depends('date_time', 'total_hours')
    def _compute_office_hours(self):
        for record in self:
            if not record.date_time or not record.total_hours:
                record.office_hours = 0.0
                continue

            # تعریف بازه کاری کارمند
            work_start = record.date_time
            work_end = work_start + timedelta(hours=record.total_hours)

            # تعریف بازه کاری اداری (همان روز)
            office_start = datetime.combine(record.date, time(5,30))
            office_end = datetime.combine(record.date, time(14,30))

            # محاسبه شروع و پایان مشترک
            overlap_start = max(work_start, office_start)
            overlap_end = min(work_end, office_end)

            if overlap_start < overlap_end:
                overlap_seconds = (overlap_end - overlap_start).total_seconds()
                office_hours_calculated = overlap_seconds / 3600

                # محدود کردن به حداکثر 8 ساعت
                record.office_hours = min(office_hours_calculated, 8.0)
            else:
                record.office_hours = 0.0


    @api.depends('date_time', 'total_hours', 'office_hours')
    def _compute_overtime(self):
        for record in self:
            if not record.date_time or not record.total_hours:
                record.hours_18_22 = 0.0
                continue

            # محاسبه ساعت‌های اضافی بالاتر از 8 ساعت در بازه اداری
            overtime_from_office = max(0, record.total_hours - 8.0)

            # تعریف بازه کاری کارمند
            work_start = record.date_time
            work_end = work_start + timedelta(hours=record.total_hours)

            # تعریف بازه اضافه کاری (18-22)
            overtime_start = datetime.combine(record.date, time(18,0))
            overtime_end = datetime.combine(record.date, time(22,0))

            # محاسبه ساعت‌های اضافه کاری در بازه 18-22
            overtime_overlap_start = max(work_start, overtime_start)
            overtime_overlap_end = min(work_end, overtime_end)

            if overtime_overlap_start < overtime_overlap_end:
                overtime_seconds = (overtime_overlap_end - overtime_overlap_start).total_seconds()
                overtime_hours = overtime_seconds / 3600
            else:
                overtime_hours = 0.0

            # جمع ساعت‌های اضافی از بازه اداری و بازه 18-22
            record.hours_18_22 = min(overtime_from_office + overtime_hours, 4.0)  # حداکثر 4 ساعت در بازه 18-22

    @api.depends('total_hours')
    def _compute_hours_shortage(self):
        for record in self:
            if record.total_hours < 8:
                record.hours_shortage = 8 - record.total_hours
                record.is_short_hours = True
            else:
                record.hours_shortage = 0.0
                record.is_short_hours = False

    def generate_xml_report(self, domain=None):
        """تولید گزارش XML با فرمت مورد نظر با استفاده از Office Hours و اضافه کاری"""
        if domain is None:
            domain = []

        records = self.search(domain)

        # ایجاد mapping از نام کارمند به کد
        employee_code_mapping = {
            'Boustan Sara': '0000013',
            'Glyn Lewis': '0000003',
            'Brunetti Laura': '0000009',
            'Luceri Gabriele': '0000010',
            'Salomé Carvalho': '0000011',
            'Javad Joudi': '0000012',
            'Joudi Gizem': '0000014',
            
            
        }

        # ایجاد ساختار XML مشابه فایل نمونه
        root = ET.Element("Fornitura")

        # گروه‌بندی رکوردها بر اساس employee_id
        employees = {}
        for record in records:
            employee_key = (record.employee_id.id, record.employee_id.name)
            if employee_key not in employees:
                employees[employee_key] = []
            employees[employee_key].append(record)

        # برای هر کارمند
        for (emp_id, emp_name), emp_records in employees.items():
            employee_elem = ET.SubElement(root, "Dipendente")

            # کد شرکت
            employee_elem.set("CodAziendaUfficiale", "000479")

            # کد کارمند - استفاده از mapping بر اساس نام
            employee_name_lower = emp_name.lower().strip()  # تبدیل به حروف کوچک و حذف فاصله
            employee_code = employee_code_mapping.get(employee_name_lower, str(emp_id).zfill(7))

            employee_elem.set("CodDipendenteUfficiale", employee_code)

            movimenti_elem = ET.SubElement(employee_elem, "Movimenti")
            movimenti_elem.set("GenerazioneAutomaticaDaTeorico", "N")

            # برای هر رکورد کارمند
            for record in emp_records:
                # حرکت اصلی برای ساعت کاری عادی
                if record.office_hours > 0 or record.leave_type:
                    movimento_elem = ET.SubElement(movimenti_elem, "Movimento")

                    # تعیین نوع کد بر اساس نوع رکورد
                    if record.leave_type:
                        # اگر مرخصی است
                        cod_giustificativo = self._get_leave_code(record.leave_type)
                    else:
                        # اگر تایم شیت معمولی است
                        cod_giustificativo = "OR"

                    ET.SubElement(movimento_elem, "CodGiustificativoUfficiale").text = cod_giustificativo
                    ET.SubElement(movimento_elem, "Data").text = record.date.strftime("%Y-%m-%d") if record.date else ""

                    # استفاده از office_hours به جای total_hours
                    if record.office_hours > 0:
                        hours = int(record.office_hours)
                        minutes = int((record.office_hours - hours) * 60)
                    elif record.leave_type:
                        # برای مرخصی، مقدار پیش‌فرض 8 ساعت
                        hours = 8
                        minutes = 0
                    else:
                        # برای موارد دیگر، صفر
                        hours = 0
                        minutes = 0

                    ET.SubElement(movimento_elem, "NumOre").text = str(hours).zfill(2)
                    ET.SubElement(movimento_elem, "NumMinuti").text = str(minutes).zfill(2)

                # حرکت جداگانه برای اضافه کاری (ساعت 18-22)
                if record.hours_18_22 > 0:
                    movimento_straordinario_elem = ET.SubElement(movimenti_elem, "Movimento")

                    ET.SubElement(movimento_straordinario_elem, "CodGiustificativoUfficiale").text = "ST"
                    ET.SubElement(movimento_straordinario_elem, "Data").text = record.date.strftime("%Y-%m-%d") if record.date else ""

                    # محاسبه ساعت و دقیقه اضافه کاری
                    hours_st = int(record.hours_18_22)
                    minutes_st = int((record.hours_18_22 - hours_st) * 60)

                    ET.SubElement(movimento_straordinario_elem, "NumOre").text = str(hours_st).zfill(2)
                    ET.SubElement(movimento_straordinario_elem, "NumMinuti").text = str(minutes_st).zfill(2)

                # حرکت جداگانه برای اضافه کاری شبانه (ساعت 22-06)
                if record.hours_22_06 > 0:
                    movimento_notturno_elem = ET.SubElement(movimenti_elem, "Movimento")

                    # کد مخصوص اضافه کاری شبانه
                    ET.SubElement(movimento_notturno_elem, "CodGiustificativoUfficiale").text = "STN"
                    ET.SubElement(movimento_notturno_elem, "Data").text = record.date.strftime("%Y-%m-%d") if record.date else ""

                    # محاسبه ساعت و دقیقه اضافه کاری شبانه
                    hours_notturno = int(record.hours_22_06)
                    minutes_notturno = int((record.hours_22_06 - hours_notturno) * 60)

                    ET.SubElement(movimento_notturno_elem, "NumOre").text = str(hours_notturno).zfill(2)
                    ET.SubElement(movimento_notturno_elem, "NumMinuti").text = str(minutes_notturno).zfill(2)

        # تبدیل به رشته XML
        xml_str = ET.tostring(root, encoding='utf-8', method='xml')

        return xml_str.decode('utf-8')
    
    def _get_leave_code(self, leave_type):
        
        leave_codes = {
            'FE Ferie': 'FE',
            'V6 Assegno ordinar. pagam.diretto': 'V6',
            'Permesso (Ore)':'Ore',
            'AI Assenza ingiustificata': 'AI',
            'A4 Quarantena sorv.attiva COVID19':'A4',
            'AL Allattamento': 'AL',
            'C2 Solidarieta\'aut.DLsg 148/15':'C2',
            'FR Cong.parentale a GG da 10 mesi ind.30%':'FR',
            'C5 CIG aut.(maltempo)Evento CIG':'C5',
            'C6 Solidarieta\' anticipata':'C6',
            'F2 Flessibilita\' Tipo 2':'F2',
            'FS Festività lavorata':'FS',
            'IN Infortunio':'IN',
            'LF Lavoro festivo':'LF',
            'LN Supplementare notturno':'LN',
            'LS Supplementare diurno':'LS',
            'M1 Perm.retr. per MA bimbo < 3a':'M1',
            'M2 Cong.parentale a HH da 7 a 9 mesi':'M2',
            'M3 Mal. bambino < 3 anni (MA3)':'M3',
            'M4  Prolung. congedo parentale disabili':'M4' ,
            'M5 Cong.parentale a HH entro 6 mesi':'M5',
            'M6 Cong.parentale a HH da 10 mesi non ind':'M6',
            'M7 Cong.parentale a GG da 7 a 9 mesi':'M7',
            'S5 Straord. porte chiuse festivo':'S5',
            'S3 Straord. porte chiuse feriale':'S3' ,
            'T3 Cig fondo solidarieta':'T3',
            'S4 Straord. porte aperte festivo':'S4',
            'SD Sospensione disciplinare':'SD',
            'V1 Volontariato Protezione Civile':'V1',
            'SC Sciopero':'SC',
            'SN Straordinario notturno':'SN',
            'ST Straordinario diurno':'ST',
            'V2 Assenza ingiust. no green-pass':'V2',
            'VV Cong. vittime violenza (DVV)':'VV',
            'V9 Congedo quarant.figli DL111/20':'V9',
            'VI Permessi Visite Inail':'VI',
            'VM Permessi per visita medica':'VM',
            'VO Cong. vittime viol.a ore (DVO)':'VO',
            'A5 Assenza aut. sanitarie COVID19':'A5',
            'A6 CIGO pagamento diretto':'A6',
            'A8 Congedo genitor.retrib.COVID19':'A8',
            'A9 Congedo genit.non retr.COVID19':'A9',
            'AH Assenza assunti/dimessi':'AH',
            'AP Aspettativa non retribuita':'AP',
            'AR Aspettativa Retribuita':'AR',
            'AS Assemblea sindacale':'AS',
            'BO Permessi banca ore goduti':'BO',
            'C1 Solidarieta\'antic.DLgs.148/15':'C1',
            'C3 Cig autorizz.post D.Lgs.148/15':'C3',
            'C4 CIG ant.(maltempo)Evento CIG':'C4',
            'C9 CIG autorizz. Evento Maltempo':'C9',
            'CA CIG anticipata':'CA',
            'CC CIG autorizzata (no ctr.add.)':'CC',
            'F1 Flessibilita\' Tipo 1':'F1',
            'F3 Flessibilita\' Tipo 3':'F3',
            'C7 Solidarieta\' autorizzata':'C7',
            'F7 Ferie solidarieta\' autorizzata':'F7',
            'C8 CIG anticipata Evento Maltempo':'C8',
            'CB CIG autorizzata (si ctr.add.)':'CB',
            'CP Congedo obbligatorio del padre':'CP',
            'EM Emodialisi':'EM',
            'CD Congedi straordinari disabili':'CD',
            'CF Congedo facoltativo del padre':'CF',
            'CI CIG non retribuita':'CI',
            'CM Congedo matrimoniale':'CM',
            'CV Perm. non retrib. Ctr virtuale':'CV',
            'CY Morbo Cooley':'CY',
            'DM Donazione midollo osseo':'DM',
            'DS Donazione sangue':'DS',
            'FG Flessibilita\' godute':'FG',
            'GO Giornata ad orario ridotto-GOR':'GO',
            'D2 Permessi disabili gg COVID19':'D2',
            'MF Cong.parentale a GG entro 6 mesi':'MF',
            'MI Militare':'MI',
            'MM Malattia non conta per malus':'MM',
            'MN Cong.parentale a GG da 10 mesi non ind':'MN',
            'MO Malattia ospedaliera':'MO',
            'MR Mancata certific.ricaduta mal.':'MR',
            'MT Maternita\' obbligatoria':'MT',
            'MX Malattia no trattam. speciale':'MX',
        }
        return leave_codes.get(leave_type, 'OR')  # OR به عنوان پیش‌فرض
    
    def action_export_xml(self):
        """اکشن برای دانلود فایل XML"""
        domain = []
        if self._context.get('active_ids'):
            domain = [('id', 'in', self._context.get('active_ids'))]
        
        xml_content = self.generate_xml_report(domain)
        
        # ایجاد attachment و دانلود
        attachment_id = self.env['ir.attachment'].create({
            'name': 'timesheet_report_%s.xml' % fields.Date.today(),
            'datas': base64.b64encode(xml_content.encode()),
            'type': 'binary',
        }).id
        
        download_url = '/web/content/' + str(attachment_id) + '?download=true'
        
        return {
            "type": "ir.actions.act_url",
            "url": download_url,
            "target": "self",
        }

    def init(self):
        self.env.cr.execute("DROP VIEW IF EXISTS timesheet_report")

        self.env.cr.execute("""
            CREATE VIEW timesheet_report AS (
                -- بخش تایم شیت
                SELECT
                    min(ts.id) AS id,
                    ts.employee_id,
                    ts.date,
                    ts.project_id,
                    ts.task_id,
                    min(ts.date_time) as date_time,
                    min(ts.date_time) + ((sum(ts.unit_amount) || ' hours')::interval) as end_time,
                    COALESCE(sum(ts.unit_amount), 0) as total_hours,

                    -- محاسبه office_hours (حداکثر 8 ساعت)
                    LEAST(COALESCE(
                        CASE 
                            WHEN min(ts.date_time) IS NOT NULL AND COALESCE(sum(ts.unit_amount), 0) > 0 THEN
                                EXTRACT(EPOCH FROM GREATEST(
                                    LEAST(
                                        min(ts.date_time) + ((COALESCE(sum(ts.unit_amount), 0) || ' hours')::interval),
                                        date_trunc('day', min(ts.date_time)) + interval '14 hours 30 minutes'
                                    ) - GREATEST(
                                        min(ts.date_time),
                                        date_trunc('day', min(ts.date_time)) + interval '5 hours 30 minutes'
                                    ),
                                    interval '0 second'
                                )) / 3600
                            ELSE 0
                        END, 0
                    ), 8.0) AS office_hours,

                    -- محاسبه hours_18_22 با در نظر گرفتن ساعت‌های اضافی
                    COALESCE(
                        EXTRACT(EPOCH FROM GREATEST(
                            LEAST(
                                min(ts.date_time) + ((sum(ts.unit_amount) || ' hours')::interval),
                                date_trunc('day', min(ts.date_time)) + interval '22 hours'
                            ) - GREATEST(
                                min(ts.date_time),
                                date_trunc('day', min(ts.date_time)) + interval '18 hours'
                            ),
                            interval '0 second'
                        )) / 3600, 0
                    ) + 
                    GREATEST(0, COALESCE(sum(ts.unit_amount), 0) - 8.0) AS hours_18_22,

                    -- محاسبه hours_22_06 (بدون تغییر)
                    COALESCE(
                        EXTRACT(EPOCH FROM GREATEST(
                            LEAST(
                                min(ts.date_time) + ((sum(ts.unit_amount) || ' hours')::interval),
                                date_trunc('day', min(ts.date_time)) + interval '1 day' + interval '3 hours 30 minutes'
                            ) - GREATEST(
                                min(ts.date_time),
                                date_trunc('day', min(ts.date_time)) + interval '18 hours 30 minutes'
                            ),
                            interval '0 second'
                        )) / 3600, 0
                    ) AS hours_22_06,

                    -- روز هفته
                    CASE 
                        WHEN EXTRACT(DOW FROM ts.date) = 0 THEN 'Sunday'
                        WHEN EXTRACT(DOW FROM ts.date) = 1 THEN 'Monday'
                        WHEN EXTRACT(DOW FROM ts.date) = 2 THEN 'Tuesday'
                        WHEN EXTRACT(DOW FROM ts.date) = 3 THEN 'Wednesday'
                        WHEN EXTRACT(DOW FROM ts.date) = 4 THEN 'Thursday'
                        WHEN EXTRACT(DOW FROM ts.date) = 5 THEN 'Friday'
                        WHEN EXTRACT(DOW FROM ts.date) = 6 THEN 'Saturday'
                    END AS day_of_week,

                    CASE 
                        WHEN EXTRACT(DOW FROM ts.date) IN (0, 6) THEN true
                        ELSE false
                    END AS is_weekend,

                    -- محاسبات تاخیر
                    CASE 
                        WHEN MIN(ts.date_time) > (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes')
                        THEN EXTRACT(EPOCH FROM (MIN(ts.date_time) - (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes'))) / 3600
                        ELSE 0
                    END AS delay_hours,

                    CASE 
                        WHEN MIN(ts.date_time) > (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes') 
                        THEN EXTRACT(EPOCH FROM (MIN(ts.date_time) - (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes'))) / 60
                        ELSE 0
                    END::integer AS delay_minutes,

                    CASE 
                        WHEN MIN(ts.date_time) > (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes')
                        THEN true
                        ELSE false
                    END AS is_delayed,

                    CASE
                        WHEN MIN(ts.date_time) > (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes')
                        THEN 
                            (FLOOR(EXTRACT(EPOCH FROM (MIN(ts.date_time) - (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes'))) / 3600)::text
                            || 'h ' ||
                            FLOOR(
                                MOD(
                                    EXTRACT(EPOCH FROM (MIN(ts.date_time) - (date_trunc('day', MIN(ts.date_time)) + interval '5 hours 30 minutes')))::numeric,
                                    3600
                                ) / 60
                            )::text
                            || 'm')
                        ELSE '0h 0m'
                    END AS delay_display,

                    -- فیلدهای مرخصی
                    NULL::integer AS leave_id,
                    NULL::date AS leave_start,
                    NULL::date AS leave_end,
                    NULL::varchar AS leave_type

                FROM account_analytic_line ts
                WHERE ts.project_id IS NOT NULL 
                AND ts.employee_id IS NOT NULL
                AND ts.unit_amount > 0
                GROUP BY ts.employee_id, ts.date, ts.project_id, ts.task_id

                UNION ALL

                -- بخش مرخصی
                SELECT
                    -hl.id AS id,
                    hl.employee_id,
                    hl.request_date_from::date AS date,
                    NULL::integer AS project_id,
                    NULL::integer AS task_id,
                    CAST(hl.request_date_from AS date) AS start_time,
                    CAST(hl.request_date_to AS date) AS end_time,
                    0 AS total_hours,
                    0 AS office_hours,
                    0 AS hours_18_22,
                    0 AS hours_22_06,
                    CASE 
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 0 THEN 'Sunday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 1 THEN 'Monday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 2 THEN 'Tuesday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 3 THEN 'Wednesday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 4 THEN 'Thursday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 5 THEN 'Friday'
                        WHEN EXTRACT(DOW FROM hl.request_date_from) = 6 THEN 'Saturday'
                    END AS day_of_week,
                    CASE 
                        WHEN EXTRACT(DOW FROM hl.request_date_from) IN (0, 6) THEN true
                        ELSE false
                    END AS is_weekend,
                    NULL::float AS delay_hours,
                    NULL::integer AS delay_minutes,
                    NULL::boolean AS is_delayed,
                    NULL::varchar AS delay_display,
                    hl.id AS leave_id,
                    hl.request_date_from::date AS date_time,
                    hl.request_date_to::date AS end_time,
                    ltype.name AS leave_type
                FROM hr_leave hl
                JOIN hr_leave_type ltype ON ltype.id = hl.holiday_status_id
                WHERE hl.state = 'validate'
            )
        """)