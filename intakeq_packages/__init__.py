"""Reconstruct PracticeQ / IntakeQ appointment-package balances from the public API.

IntakeQ has no /packages endpoint. Package membership is exposed on every appointment
(AppointmentPackageId / AppointmentPackageName) and package purchases appear as invoice
line items, so balances are rebuilt from those two feeds plus a local mirror of the
package definitions. See README.md.
"""

from .client import IntakeQClient, IntakeQError
from .packages import PackageConfig, PackageLedger, build_ledger

__all__ = ["IntakeQClient", "IntakeQError", "PackageConfig", "PackageLedger", "build_ledger"]
