import logging

class VetoEngine:
    def __init__(self, gsl):
        self.gsl = gsl
        self.logger = logging.getLogger("VetoEngine")
        try:
            from lib.protocols.ufp_bridge import UFPBridge
            self.bridge = UFPBridge()
        except Exception as e:
            self.logger.warning(f"UFP Bridge unavailable: {e}")
            self.bridge = None

    def handle_message(self, message):
        if message.priority == 0: # CRITICAL
            self.logger.info("VETO_CHECK: Monitoring critical traffic.")
            
    def trigger_veto(self, target_agent: str):
        self.logger.critical(f"VETO_COMMAND_ISSUED: Halting {target_agent}")
        if self.bridge:
            self.bridge.send_task(target_agent, "VETO_SHUTDOWN")
        else:
            self.logger.warning("UFP Bridge not available, veto command not sent")
