from __future__ import annotations

import argparse
import asyncio
import json

from .agent import AgenticQA
from .models import QARequest


async def main_async() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--max-sources", type=int, default=5)
    args = parser.parse_args()
    response = await AgenticQA().answer(QARequest(question=args.question, max_sources=args.max_sources))
    print(json.dumps(response.model_dump(), indent=2, ensure_ascii=False))


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
