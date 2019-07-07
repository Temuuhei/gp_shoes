# -*- coding: utf-8 -*-
{
    'name': 'Preview Report PDF in Browser',
    'version': '10.0.1.0',
    'summary': """Preview PDF Reports in Browser""",
    'author': 'Ivan Sokolov, Ahmed Khakwani',
    'category': 'Productivity',
    'license': 'GPL-3',
    'website': 'https://demo.cetmix.com',
    'live_test_url': 'https://demo.cetmix.com',
    'description': """
    Preview reports in browser instead of downloading them.
    Open Report in new tab instead of downloading.              
""",
    'depends': ['base', 'web'],
    'images': ['static/description/banner.png'],
    'data': [
        'views/prt_report_preview_template.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
