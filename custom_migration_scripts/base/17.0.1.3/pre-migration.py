"""
Custom pre-migration script for OpenUpgrade from Odoo 15/16 to Odoo 17

This script runs automatically BEFORE the standard OpenUpgrade base pre-migration.
It fixes known issues that would otherwise cause the migration to fail.

Location: custom_migration_scripts/base/17.0.1.3/pre-migration.py
"""

import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Pre-migration fixes for OpenUpgrade.
    
    This function is called automatically by OpenUpgrade before the base module
    migration scripts run.
    """
    if not version:
        return
    
    _logger.info("=" * 60)
    _logger.info("Running custom pre-migration fixes...")
    _logger.info("=" * 60)
    
    # Fix 1: Disable old FatturaPA cron job
    _fix_fatturapa_cron(cr)
    
    # Fix 2: Set noupdate for EDI formats with linked documents
    _fix_edi_format_noupdate(cr)
    
    # Fix 3: Remove project.delete.wizard references
    _fix_project_delete_wizard(cr)
    
    # Fix 4: Remove incompatible settings views (old xpath expressions)
    _fix_incompatible_settings_views(cr)
    
    _logger.info("=" * 60)
    _logger.info("Custom pre-migration fixes completed!")
    _logger.info("=" * 60)


def _fix_fatturapa_cron(cr):
    """
    Disable the old FatturaPA cron job.
    
    In Odoo 17, the method `_cron_receive_fattura_pa` on `account.edi.format`
    no longer exists. It was replaced by `cron_l10n_it_edi_download_and_update` on `account.move`.
    """
    _logger.info("Fixing FatturaPA cron job...")
    
    # cron_name is jsonb in Odoo 17, so we need to cast it to text for LIKE
    cr.execute("""
        UPDATE ir_cron 
        SET active = false 
        WHERE cron_name::text LIKE '%%FatturaPA%%' 
          AND active = true
        RETURNING id, cron_name
    """)
    disabled_crons = cr.fetchall()
    
    for cron_id, cron_name in disabled_crons:
        _logger.info(f"  Disabled cron job: {cron_name} (id={cron_id})")
    
    if not disabled_crons:
        _logger.info("  No FatturaPA cron jobs to disable")


def _fix_edi_format_noupdate(cr):
    """
    Set noupdate=True for all account.edi.format records that have linked documents.
    
    This prevents foreign key constraint errors when OpenUpgrade tries to delete
    EDI formats that are still referenced by account.edi.document records.
    """
    _logger.info("Fixing EDI format noupdate flags...")
    
    # First, check if account_edi_document table exists
    cr.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'account_edi_document'
        )
    """)
    if not cr.fetchone()[0]:
        _logger.info("  Table account_edi_document does not exist, skipping")
        return
    
    # Set noupdate=True for edi_fatturaPA specifically
    cr.execute("""
        UPDATE ir_model_data 
        SET noupdate = true 
        WHERE module = 'l10n_it_edi' 
          AND name = 'edi_fatturaPA'
          AND noupdate = false
        RETURNING id
    """)
    if cr.fetchall():
        _logger.info("  Set noupdate=True for edi_fatturaPA")
    
    # Set noupdate=True for ALL account.edi.format records that have linked documents
    cr.execute("""
        UPDATE ir_model_data 
        SET noupdate = true 
        WHERE model = 'account.edi.format'
          AND noupdate = false
          AND res_id IN (
              SELECT DISTINCT edi_format_id 
              FROM account_edi_document 
              WHERE edi_format_id IS NOT NULL
          )
        RETURNING id, name
    """)
    updated = cr.fetchall()
    
    for rec_id, name in updated:
        _logger.info(f"  Set noupdate=True for EDI format: {name} (id={rec_id})")
    
    if not updated:
        _logger.info("  No additional EDI formats needed noupdate fix")


def _fix_project_delete_wizard(cr):
    """
    Remove references to project.delete.wizard which was removed in Odoo 17.
    """
    _logger.info("Fixing project.delete.wizard references...")
    
    # Check if ir_model table has the project.delete.wizard model
    cr.execute("""
        SELECT id FROM ir_model WHERE model = 'project.delete.wizard'
    """)
    model_ids = cr.fetchall()
    
    if not model_ids:
        _logger.info("  No project.delete.wizard model found")
        return
    
    # Remove from ir.model.access
    cr.execute("""
        DELETE FROM ir_model_access 
        WHERE model_id IN (
            SELECT id FROM ir_model WHERE model = 'project.delete.wizard'
        )
        RETURNING id
    """)
    deleted = cr.fetchall()
    if deleted:
        _logger.info(f"  Removed {len(deleted)} access rules for project.delete.wizard")
    
    # Remove from ir.model.data
    cr.execute("""
        DELETE FROM ir_model_data 
        WHERE name LIKE '%%project_delete_wizard%%'
        RETURNING id, name
    """)
    deleted = cr.fetchall()
    for rec_id, name in deleted:
        _logger.info(f"  Removed ir.model.data: {name} (id={rec_id})")


def _delete_view_cascade(cr, view_id, view_name, module):
    """
    Delete a view and all its child views recursively.
    Returns the count of deleted views.
    """
    deleted_count = 0
    
    # First, find and delete all child views that inherit from this view
    cr.execute("""
        SELECT id, name FROM ir_ui_view WHERE inherit_id = %s
    """, (view_id,))
    child_views = cr.fetchall()
    
    for child_id, child_name in child_views:
        deleted_count += _delete_view_cascade(cr, child_id, child_name, module)
    
    # Delete from ir_model_data first
    cr.execute("""
        DELETE FROM ir_model_data 
        WHERE res_id = %s AND model = 'ir.ui.view'
    """, (view_id,))
    
    # Then delete the view itself
    cr.execute("""
        DELETE FROM ir_ui_view WHERE id = %s
        RETURNING id, name
    """, (view_id,))
    
    deleted = cr.fetchone()
    if deleted:
        _logger.info(f"  Removed incompatible view: {view_name} (id={view_id}, module={module})")
        deleted_count += 1
    
    return deleted_count


def _fix_incompatible_settings_views(cr):
    """
    Remove settings views with incompatible xpath expressions.
    
    In Odoo 17, the settings view structure changed significantly:
    - //div[hasclass('settings')] no longer exists
    - //div[@id='account_vendor_bills'] may not exist in some contexts
    
    These old views will be recreated correctly when modules are updated.
    This ensures no feature is lost - just the old incompatible views are removed
    so the new Odoo 17 compatible views can be loaded.
    """
    _logger.info("Fixing incompatible settings views...")
    
    # List of problematic xpath patterns that don't work in Odoo 17
    problematic_patterns = [
        # Old settings structure
        "%hasclass('settings')%",
        "%hasclass(''settings'')%",
        # Old account settings structure (for Italian EDI and similar)
        "%@id='account_vendor_bills'%",
        "%@id=''account_vendor_bills''%",
    ]
    
    total_deleted = 0
    
    for pattern in problematic_patterns:
        # Find views with this pattern in res.config.settings model
        cr.execute("""
            SELECT v.id, v.name, d.module
            FROM ir_ui_view v
            LEFT JOIN ir_model_data d ON d.res_id = v.id AND d.model = 'ir.ui.view'
            WHERE v.model = 'res.config.settings'
              AND v.inherit_id IS NOT NULL
              AND v.arch_db::text LIKE %s
        """, (pattern,))
        
        views_to_delete = cr.fetchall()
        
        for view_id, view_name, module in views_to_delete:
            total_deleted += _delete_view_cascade(cr, view_id, view_name, module)
    
    if total_deleted == 0:
        _logger.info("  No incompatible settings views found")
    else:
        _logger.info(f"  Total: {total_deleted} incompatible views removed")

