import enum


class UpdateStatus(enum.Enum):
    AVAILABLE = "available"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"
