"""IAM policy management for AWS Bedrock."""

import json


class IAMPolicyManager:
    """Generate and validate IAM policies for Bedrock.

    Implements least-privilege access patterns.

    Example:
        >>> manager = IAMPolicyManager()
        >>> policy = manager.generate_least_privilege_policy()
        >>> print(json.dumps(policy, indent=2))
    """

    def generate_least_privilege_policy(
        self,
        regions: list[str] | None = None,
        models: list[str] | None = None,
    ) -> dict:
        """Generate minimal IAM policy for Bedrock access.

        Args:
            regions: Allowed AWS regions (defaults to ["us-east-1"])
            models: Allowed model patterns (defaults to ["anthropic.claude-sonnet-4-*"])

        Returns:
            dict: IAM policy document

        Example:
            >>> manager = IAMPolicyManager()
            >>> policy = manager.generate_least_privilege_policy(
            ...     regions=["us-east-1", "us-west-2"],
            ...     models=["anthropic.claude-*"],
            ... )
        """
        if regions is None:
            regions = ["us-east-1"]

        if models is None:
            models = ["anthropic.claude-sonnet-4-*"]

        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "BedrockModelInvocation",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                    ],
                    "Resource": [
                        f"arn:aws:bedrock:*::foundation-model/{model}"
                        for model in models
                    ],
                    "Condition": {"StringEquals": {"aws:RequestedRegion": regions}},
                },
                {
                    "Sid": "BedrockInferenceProfiles",
                    "Effect": "Allow",
                    "Action": "bedrock:ListInferenceProfiles",
                    "Resource": "*",
                },
            ],
        }

    def to_json(self, policy: dict, indent: int = 2) -> str:
        """Convert policy to JSON string.

        Args:
            policy: IAM policy document
            indent: JSON indentation

        Returns:
            str: JSON string
        """
        return json.dumps(policy, indent=indent)

    def save_to_file(self, policy: dict, filepath: str) -> None:
        """Save policy to file.

        Args:
            policy: IAM policy document
            filepath: Output file path
        """
        with open(filepath, "w") as f:
            json.dump(policy, f, indent=2)
