with open("models/group.py") as f:
    content = f.read()

content = content.replace(
    "from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text",
    "from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Integer, String, Text",
)

content = content.replace(
    "    default_swear_duration: Mapped[int] = mapped_column(\n        Integer, default=300, nullable=False\n    )",
    "    default_swear_duration: Mapped[int] = mapped_column(\n        Integer, default=300, nullable=False\n    )\n\n    locked_media: Mapped[dict[str, bool]] = mapped_column(\n        JSON, default=dict, nullable=False\n    )",
)

with open("models/group.py", "w") as f:
    f.write(content)
