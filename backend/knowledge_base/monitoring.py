from datetime import datetime


# ==========================================
# KNOWLEDGE BASE MONITOR
# ==========================================

class KnowledgeBaseMonitor:

    def __init__(self):

        self.metrics = {
            "documents_processed": 0,
            "documents_activated": 0,
            "documents_failed": 0,
            "documents_quarantined": 0,
            "escalations": 0,
            "total_processing_time_ms": 0,
            "quality_scores": []
        }

    # ======================================
    # RECORD PROCESSING
    # ======================================

    def record_processing(
        self,
        processing_time_ms,
        success=True
    ):

        self.metrics[
            "documents_processed"
        ] += 1

        self.metrics[
            "total_processing_time_ms"
        ] += processing_time_ms

        if not success:

            self.metrics[
                "documents_failed"
            ] += 1

    # ======================================
    # RECORD ACTIVATION
    # ======================================

    def record_activation(
        self,
        success=True
    ):

        if success:

            self.metrics[
                "documents_activated"
            ] += 1

        else:

            self.metrics[
                "documents_failed"
            ] += 1

    # ======================================
    # RECORD QUARANTINE
    # ======================================

    def record_quarantine(self):

        self.metrics[
            "documents_quarantined"
        ] += 1

    # ======================================
    # RECORD ESCALATION
    # ======================================

    def record_escalation(self):

        self.metrics[
            "escalations"
        ] += 1

    # ======================================
    # RECORD QUALITY
    # ======================================

    def record_quality(
        self,
        score
    ):

        self.metrics[
            "quality_scores"
        ].append(score)

    # ======================================
    # AVERAGE PROCESSING TIME
    # ======================================

    def average_processing_time(self):

        processed = self.metrics[
            "documents_processed"
        ]

        if processed == 0:

            return 0

        return round(
            self.metrics[
                "total_processing_time_ms"
            ] / processed,
            2
        )

    # ======================================
    # HEALTH CHECK
    # ======================================

    def health_check(self):

        processed = self.metrics[
            "documents_processed"
        ]

        failed = self.metrics[
            "documents_failed"
        ]

        if processed == 0:

            failure_rate = 0

        else:

            failure_rate = (
                failed / processed
            ) * 100

        healthy = failure_rate < 20

        return {
            "healthy": healthy,

            "status": (
                "HEALTHY"
                if healthy
                else "UNHEALTHY"
            ),

            "failure_rate_percent":
                round(
                    failure_rate,
                    2
                ),

            "average_processing_time_ms":
                self.average_processing_time(),

            "checked_at":
                datetime.now().isoformat()
        }

    # ======================================
    # GET METRICS
    # ======================================

    def get_metrics(self):

        return {
            **self.metrics,

            "average_processing_time_ms":
                self.average_processing_time()
        }


# ==========================================
# TEST
# ==========================================

if __name__ == "__main__":

    monitor = KnowledgeBaseMonitor()

    print("\nKnowledge Base Monitoring")
    print("=========================")

    monitor.record_processing(
        processing_time_ms=120,
        success=True
    )

    monitor.record_processing(
        processing_time_ms=180,
        success=True
    )

    monitor.record_activation(
        success=True
    )

    monitor.record_quarantine()

    monitor.record_escalation()

    monitor.record_quality(0.95)
    monitor.record_quality(0.91)

    print("\nMetrics:")
    print(
        monitor.get_metrics()
    )

    print("\nHealth Check:")
    print(
        monitor.health_check()
    )