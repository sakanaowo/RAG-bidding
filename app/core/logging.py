import logging, sys, json
from app.core.config import settings


class JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        base = {
            "level": r.levelname,
            "time": self.formatTime(r, self.datefmt),
            "message": r.getMessage(),
            "logger": r.name,
        }
        if r.exc_info:
            base["exc_info"] = self.formatException(r.exc_info)
        return json.dumps(base)


def setup_logging():
    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if settings.log_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))

    root.addHandler(handler)
