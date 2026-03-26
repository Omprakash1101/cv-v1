"""
serializers.py
Validates the incoming POST payload for ProjectDiagramView.
"""

from rest_framework import serializers


class ProjectAnalysisSerializer(serializers.Serializer):
    """
    Fields
    ------
    code         : raw Django code string  (optional if project_zip provided)
    project_zip  : uploaded .zip file      (optional if code provided)
    format       : "json" or "html"        (default: "json")
    """

    code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Paste Django view / model / serializer code here.",
    )

    project_zip = serializers.FileField(
        required=False,
        help_text="Upload a .zip of your Django project folder.",
    )

    format = serializers.ChoiceField(
        choices=["json", "html"],
        default="json",
        help_text="Response format: 'json' or 'html'.",
    )

    # ── Cross-field validation ─────────────────
    def validate(self, attrs):
        code        = attrs.get("code", "").strip()
        project_zip = attrs.get("project_zip", None)

        if not code and not project_zip:
            raise serializers.ValidationError(
                "You must supply either 'code' (string) or 'project_zip' (file)."
            )
        return attrs