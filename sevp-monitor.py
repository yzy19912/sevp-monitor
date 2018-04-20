#!/usr/bin/env python3

# SEVP Monitor
# Copyright (C) 2018 Yunzhu Li
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
import datetime
import json
import smtplib
import sys
import time
from email.mime.text import MIMEText
from urllib import request, parse

# SEVP user configurations
sevp_email = ''
sevp_password = ''

# Email notification configurations (optional)
notification_email_address = ''
smtp_server = ''
smtp_user = ''
smtp_password = ''


# Start monitoring
def start_monitor():
    jwt = sevp_login(sevp_email, sevp_password)
    last_num_history = -1
    while True:
        history = sevp_get_student_history(jwt)
        if history is None:
            # Failed to fetch history, try logging in again
            jwt = sevp_login(sevp_email, sevp_password)
            time.sleep(5)
            continue

        # Check number of history
        num_history = len(history)

        if last_num_history == -1:
            last_num_history = num_history

        if num_history > last_num_history:
            # New history item found
            print('[INFO] New history item found, number of items:', num_history)
            send_notification_email()
            sys.exit(0)
        else:
            datetime_str = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            print('[INFO]', datetime_str, 'Number of history items:', num_history)

        time.sleep(300) # Check once per five minutes


# Login and get a jwt
def sevp_login(email, password):
    print('[INFO] Logging in...')

    # POST data
    data = {'email': email, 'password': password}
    data = str(json.dumps(data))
    data = data.encode('utf-8')

    # Prepare request
    req = request.Request('https://sevp.ice.gov/optapp/rest/loginLogout/login', data=data)
    req.add_header('Content-Type', 'application/json')

    # Send request
    try:
        res = request.urlopen(req)
        res_obj = json.loads(res.read())
    except:
        # If request fails or cannot parse json
        print('[ERROR] Failed to login')
        sys.exit(1)

    jwt = res_obj['value']
    if len(jwt.split('.')) != 3:
        print('[ERROR] Failed to parse JWT')
        sys.exit(1)

    return jwt


# Get student profile update history
def sevp_get_student_history(jwt):
    print('[INFO] Fetching history...')

    # Get user ID from JWT
    user_id = extract_user_id(jwt)

    # Send empty POST request with JWT attached
    data = bytearray()
    req = request.Request('https://sevp.ice.gov/optapp/rest/students/studentHistory/' + user_id, data=data)
    req.add_header('Authorization', 'Bearer ' + jwt)

    # Send request
    try:
        res = request.urlopen(req)
        res_obj = json.loads(res.read())
    except:
        # If request fails or cannot parse json
        return None

    return res_obj


# Decode JWT and get user_id
def extract_user_id(jwt):
    # Split to 3 parts
    jwt_parts = jwt.split('.')

    # Decode payload (second part)
    payload_data = base64.urlsafe_b64decode(jwt_parts[1] + '=' * (4 - len(jwt_parts[1]) % 4))

    # Parse as JSON
    payload = json.loads(payload_data)
    return payload['sub']


# Send email with pre-defined text
def send_notification_email():
    # Skip if not configured
    if len(notification_email_address) == 0:
        return

    print('[INFO] Sending notification email...')

    # Construct message
    msg = MIMEText('New SEVP history found')
    msg['Subject'] = 'SEVP Monitor Notification'
    msg['From'] = notification_email_address
    msg['To'] = notification_email_address

    # Connection (TLS)
    smtp = smtplib.SMTP(smtp_server, 587)
    smtp.starttls()
    smtp.login(smtp_user, smtp_password)
    smtp.send_message(msg)
    smtp.quit()

    print('[INFO] Email sent')

# Entry point
if __name__ == '__main__':
    start_monitor()
