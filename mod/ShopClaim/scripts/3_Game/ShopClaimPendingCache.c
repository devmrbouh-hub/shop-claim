class ShopClaimPendingCacheEntry
{
	ref array<ref ShopClaimPendingOrder> Orders;
	int ExpiresAtMs;

	void ShopClaimPendingCacheEntry()
	{
		Orders = new array<ref ShopClaimPendingOrder>();
	}
};

class ShopClaimPendingCache
{
	protected static const int TTL_MS = 300000;
	protected ref map<string, ref ShopClaimPendingCacheEntry> m_Entries;

	void ShopClaimPendingCache()
	{
		m_Entries = new map<string, ref ShopClaimPendingCacheEntry>();
	}

	void Store(string steamId, array<ref ShopClaimPendingOrder> orders)
	{
		ref ShopClaimPendingCacheEntry entry = new ShopClaimPendingCacheEntry();
		entry.Orders = orders;
		entry.ExpiresAtMs = GetGame().GetTime() + TTL_MS;
		m_Entries.Set(steamId, entry);
	}

	bool TryGet(string steamId, out array<ref ShopClaimPendingOrder> orders)
	{
		orders = null;
		if (!m_Entries.Contains(steamId))
			return false;

		ref ShopClaimPendingCacheEntry entry = m_Entries.Get(steamId);
		if (!entry)
			return false;

		if (GetGame().GetTime() > entry.ExpiresAtMs)
		{
			m_Entries.Remove(steamId);
			return false;
		}

		orders = entry.Orders;
		return orders != null;
	}

	ShopClaimPendingOrder GetByIndex(string steamId, int index1Based)
	{
		array<ref ShopClaimPendingOrder> orders;
		if (!TryGet(steamId, orders) || !orders)
			return null;

		int idx = index1Based - 1;
		if (idx < 0 || idx >= orders.Count())
			return null;

		return orders.Get(idx);
	}

	ShopClaimPendingOrder GetByOperationId(string steamId, string operationId)
	{
		if (!operationId || operationId == "")
			return null;

		array<ref ShopClaimPendingOrder> orders;
		if (!TryGet(steamId, orders) || !orders)
			return null;

		foreach (ShopClaimPendingOrder order : orders)
		{
			if (order && order.operation_id == operationId)
				return order;
		}

		return null;
	}

	void RemoveOrder(string steamId, string operationId)
	{
		if (!steamId || steamId == "" || !operationId || operationId == "")
			return;

		if (!m_Entries.Contains(steamId))
			return;

		ref ShopClaimPendingCacheEntry entry = m_Entries.Get(steamId);
		if (!entry || !entry.Orders)
			return;

		for (int i = entry.Orders.Count() - 1; i >= 0; i--)
		{
			ShopClaimPendingOrder order = entry.Orders.Get(i);
			if (order && order.operation_id == operationId)
			{
				entry.Orders.Remove(i);
				break;
			}
		}

		if (entry.Orders.Count() == 0)
			m_Entries.Remove(steamId);
	}

	void Invalidate(string steamId)
	{
		if (!steamId || steamId == "")
			return;

		m_Entries.Remove(steamId);
	}
};
