# ISALAB Odoo 17 Custom Modules

Custom addons and configuration for Odoo 17 (migrated from Odoo 16).

## 📁 Structure

```
isalab17-custom/
├── custom_addons/           # Custom modules (migrated)
├── custom_3rdP_addons/      # Third-party modules
│   ├── module_from_oca/
│   └── module_from_other_vendor/
├── custom_migration_scripts/ # Migration scripts
├── isa17.cfg.template       # Configuration template
└── README.md
```

## 🚀 Setup

```bash
# Clone into /opt/odoo/
cd /opt/odoo
git clone https://github.com/A-zeril-A/isalab17-custom.git isalab17-custom

# Run setup script (from isalab15-custom)
cd /opt/odoo/isalab15-custom/scripts
sudo ./setup_odoo_version.sh 17
```

## 🔄 Migration from v16

Use the migration backup from Odoo 16.

## 🚀 Start Odoo 17

```bash
sudo -u odoo -H /opt/odoo/isalab17/venv_isalab17/bin/python3 \
  /opt/odoo/isalab17/odoo-bin -c /opt/odoo/isalab17/config/isa17.cfg
```

Web: http://SERVER_IP:8017

