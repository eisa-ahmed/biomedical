# -*- coding: utf-8 -*-
{
    'name': "MRP Biomedical",

    'summary': "Advanced manufacturing process management for the biomedical industry with custom BoM templates, process dependencies, work order signatures, operation time tracking, and order tracking features.",

    'description': """
The MrpBioMedical module enhances Odoo's Manufacturing Resource Planning (MRP) system specifically for the biomedical industry. Key features include customized bill of materials (BoM) templates, management of process dependencies, work order sign-off capabilities, detailed operation time tracking, and advanced filtering for tracking past orders. This module ensures efficient and traceable manufacturing operations, maintaining standardized workflows, accountability, and robust historical data management.
    """,

    'author': "EisaA",
    'website': "https://www.fiverr.com/eisaahmed63",
    'category': 'Manufacturing',
    'version': '17.0.1.0',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_template_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
