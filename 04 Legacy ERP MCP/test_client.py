import asyncio
from fastmcp import Client


async def main():
    client = Client("server.py")

    async with client:
        tools = await client.list_tools()
        print("=== Tools ===")
        for t in tools:
            print("-", t.name)

        result1 = await client.call_tool("find_inventory", {"item_code": "ITEM-001"})
        print("\n=== find_inventory ===")
        print(result1)

        result2 = await client.call_tool("list_low_stock", {"threshold": 10})
        print("\n=== list_low_stock ===")
        print(result2)

        result3 = await client.call_tool("find_purchase_orders", {"status": "APPROVED"})
        print("\n=== find_purchase_orders ===")
        print(result3)

        result4 = await client.call_tool(
            "adjust_inventory",
            {
                "item_code": "ITEM-002",
                "delta": 5,
                "reason": "실습용 재고 보정"
            }
        )
        print("\n=== adjust_inventory ===")
        print(result4)


if __name__ == "__main__":
    asyncio.run(main())
