class ShopClaimPlayerMessenger
{
	static void Send(PlayerBase player, string text)
	{
		if (!player || !player.GetIdentity())
			return;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		string prefix = "";
		if (cfg && cfg.messages && cfg.messages.prefix != "")
			prefix = cfg.messages.prefix + " ";

		string full = prefix + text;
		PlayerIdentity identity = player.GetIdentity();

		Param1<string> msg = new Param1<string>(full);
		GetGame().RPCSingleParam(player, ERPCs.RPC_USER_ACTION_MESSAGE, msg, true, identity);
	}
};
