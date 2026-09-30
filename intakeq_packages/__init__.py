"""Read-only helpers for the PracticeQ / IntakeQ REST API (https://intakeq.com/api/v1).

Research outcome: IntakeQ has no /packages endpoint. Package membership is exposed per
appointment (AppointmentPackageId / AppointmentPackageName) and package sales as invoice line
items. The practice's cockpit already builds the package ledger from its own data, so this
package only documents the API surface and provides a verified, throttled client.
"""

from .client import IntakeQClient, IntakeQError

__all__ = ["IntakeQClient", "IntakeQError"]
