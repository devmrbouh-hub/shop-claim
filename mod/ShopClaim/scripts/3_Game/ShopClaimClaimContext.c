class ShopClaimClaimContextEntry
{
	string OperationId;
	ShopClaimNotifyChannel Channel;
};

class ShopClaimClaimContext
{
	protected static ref map<string, ref ShopClaimClaimContextEntry> s_BySteam;

	protected static void EnsureMap()
	{
		if (!s_BySteam)
			s_BySteam = new map<string, ref ShopClaimClaimContextEntry>();
	}

	static void Set(string steamId, string operationId, ShopClaimNotifyChannel channel)
	{
		if (!steamId || steamId == "" || !operationId || operationId == "")
			return;

		EnsureMap();

		ref ShopClaimClaimContextEntry entry = new ShopClaimClaimContextEntry();
		entry.OperationId = operationId;
		entry.Channel = channel;
		s_BySteam.Set(steamId, entry);
	}

	static bool Get(string steamId, string operationId, out ShopClaimNotifyChannel channel)
	{
		channel = ShopClaimNotifyChannel.NONE;

		if (!steamId || steamId == "" || !operationId || operationId == "")
			return false;

		if (!s_BySteam || !s_BySteam.Contains(steamId))
			return false;

		ref ShopClaimClaimContextEntry entry = s_BySteam.Get(steamId);
		if (!entry || entry.OperationId != operationId)
			return false;

		channel = entry.Channel;
		return true;
	}

	static bool Take(string steamId, string operationId, out ShopClaimNotifyChannel channel)
	{
		if (!Get(steamId, operationId, channel))
			return false;

		s_BySteam.Remove(steamId);
		return true;
	}

	static void Clear(string steamId)
	{
		if (!steamId || steamId == "" || !s_BySteam)
			return;

		s_BySteam.Remove(steamId);
	}
};
