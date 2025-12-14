import logger


def setup_logger(*, level: int = logger.INFO) -> None:
    logger.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
