from loguru import logger

logger.remove()
logger.add(
    lambda msg: print(msg, end=""),
    colorize=True,
    format="<green>{time}</green> | <level>{level}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)
