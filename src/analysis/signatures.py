"""
DSPy Signatures for Supply Chain Risk Extraction.

Defines the input/output structure for structured extraction
of risk information from unstructured news content.
"""

import dspy


class RiskExtractor(dspy.Signature):
    """
    Extract structured supply chain risk information from news content.

    This signature defines the expected input (news article) and outputs
    (structured risk data) for the extraction pipeline.
    """

    news_content: str = dspy.InputField(
        desc="The full text content of a news article or event report"
    )

    location: str = dspy.OutputField(
        desc="Geographic location of the event (city, region, or country). "
        "Return 'Unknown' if not identifiable."
    )

    company: str = dspy.OutputField(
        desc="Specific company or organization names mentioned as affected. "
        "Return 'Unknown' if no specific company is mentioned."
    )

    event_type: str = dspy.OutputField(
        desc="Type of supply chain disruption. Must be one of: "
        "Strike, Weather, Bankruptcy, Geopolitical, Fire, Pandemic, "
        "CyberAttack, Transport, or Other"
    )

    severity: str = dspy.OutputField(
        desc="Impact severity level. Must be one of: Low, Medium, High, or Critical. "
        "Consider factors like geographic scope, duration, and industry impact."
    )

    confidence: str = dspy.OutputField(
        desc="Confidence in the extraction as a decimal between 0.0 and 1.0. "
        "Lower if information is ambiguous or incomplete."
    )

    summary: str = dspy.OutputField(
        desc="Brief one-sentence summary of the supply chain risk event."
    )


class EntityExtractor(dspy.Signature):
    """
    Extract named entities relevant to supply chain analysis.

    Used for identifying companies, locations, and products mentioned in text.
    """

    text: str = dspy.InputField(desc="Text to extract entities from")

    companies: str = dspy.OutputField(
        desc="Comma-separated list of company names mentioned. "
        "Return 'None' if no companies are mentioned."
    )

    locations: str = dspy.OutputField(
        desc="Comma-separated list of geographic locations mentioned. "
        "Return 'None' if no locations are mentioned."
    )

    products: str = dspy.OutputField(
        desc="Comma-separated list of product types or categories mentioned. "
        "Return 'None' if no products are mentioned."
    )


class ImpactAssessor(dspy.Signature):
    """
    Assess the potential supply chain impact of a risk event.

    Takes extracted risk information and provides impact assessment.
    """

    event_description: str = dspy.InputField(
        desc="Description of the risk event including location and type"
    )

    affected_entities: str = dspy.InputField(
        desc="Companies or organizations affected by the event"
    )

    supply_chain_context: str = dspy.InputField(
        desc="Known supply chain relationships that may be affected"
    )

    impact_assessment: str = dspy.OutputField(
        desc="Assessment of downstream supply chain impact"
    )

    timeline_estimate: str = dspy.OutputField(
        desc="Estimated timeline for impact (immediate, days, weeks, months)"
    )

    mitigation_suggestions: str = dspy.OutputField(
        desc="Suggested mitigation strategies"
    )
