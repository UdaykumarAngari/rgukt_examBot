from exam_bot import main
import asyncio

def handler(request):
    asyncio.run(main())

    return {
        "statusCode": 200,
        "body": "OK"
    }