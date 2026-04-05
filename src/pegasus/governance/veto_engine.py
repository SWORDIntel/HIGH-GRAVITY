import logging

class VetoEngine:
    def __init__(self, gsl):
        self.gsl = gsl
        self.logger = logging.getLogger("VetoEngine")
        from tools.integration.ufp_bridge import UFPBridge
        self.bridge = UFPBridge()

    def handle_message(self, message):
        if message.priority == 0: # CRITICAL
            self.logger.info("VETO_CHECK: Monitoring critical traffic.")
            
    def trigger_veto(self, target_agent: str):
        self.logger.critical(f"VETO_COMMAND_ISSUED: Halting {target_agent}")
        self.bridge.send_task(target_agent, "VETO_SHUTDOWN")
