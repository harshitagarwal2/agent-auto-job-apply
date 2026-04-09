from jobflow.adapters.ashby import AshbyAdapter
from jobflow.adapters.glassdoor import GlassdoorAdapter
from jobflow.adapters.greenhouse import GreenhouseAdapter
from jobflow.adapters.lever import LeverAdapter
from jobflow.adapters.linkedin import LinkedInAdapter
from jobflow.adapters.workday import WorkdayAdapter
from jobflow.domain import SourceFamily


ADAPTERS = {
    SourceFamily.GREENHOUSE: GreenhouseAdapter(),
    SourceFamily.LEVER: LeverAdapter(),
    SourceFamily.ASHBY: AshbyAdapter(),
    SourceFamily.WORKDAY: WorkdayAdapter(),
    SourceFamily.LINKEDIN: LinkedInAdapter(),
    SourceFamily.GLASSDOOR: GlassdoorAdapter(),
}
