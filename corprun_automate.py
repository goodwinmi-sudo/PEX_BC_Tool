import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

import pexpect
import sys

child = pexpect.spawn('/google/bin/releases/corprun-cli/corprun', ['init', '--system_name=deal-reviewer', '--team_group=ml-gemini-users-tier-1', '--buganizer_component=1192591', '--contact_email=goodwinmi@google.com'])
child.logfile = sys.stdout.buffer

try:
    child.expect('(?i)admin group', timeout=10)
    child.sendline('ml-gemini-downstream-grpadm')
    
    child.expect('(?i)approver', timeout=5)
    child.sendline('goodwinmi')
    
    child.expect('(?i)yes/no', timeout=10)
    child.sendline('yes')
    
    child.expect(pexpect.EOF, timeout=120)
    logger.info("Finished.")
except Exception as e:
    logger.info(str(e))
