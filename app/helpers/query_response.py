from flask import Flask, render_template
import telegram
import datetime

def announcement_message(announcements):
    announcement_inputs = []
    announcements = list(announcements)
    for announcement in announcements:
        just_in = False
        if announcement.announced_date >= datetime.datetime.now() - datetime.timedelta(days=1):
            just_in = True
        announcement_input = {
                'just_in': just_in,
                'announced_company': announcement.announced_company.company_name,
                'announcement_title': announcement.title,
                'announced_date': str(announcement.announced_date.date().strftime('%d/%m/%Y')),
                'ann_id': announcement.ann_id
                }
        announcement_inputs.append(announcement_input)
    return render_template('message_template.html', announcement_inputs=announcement_inputs)
