import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

import pexpect
import sys

try:
    child = pexpect.spawn('gcert', timeout=30)
    child.logfile = sys.stdout.buffer
    
    # Wait for completion or prompt
    index = child.expect(['(?i)password', '(?i)touch your security key', pexpect.EOF, pexpect.TIMEOUT])
    
    if index == 0:
        logger.info("\ngcert wants a password")
    elif index == 1:
        logger.info("\ngcert wants a yubikey touch")
    elif index == 2:
        logger.info("\ngcert finished successfully")
    elif index == 3:
        logger.info("\ngcert timed out")
except Exception as e:
    logger.info(f"Error: {e}")
