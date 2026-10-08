class ShopClaimGuiRpc
{
	protected static ref ShopClaimGuiRpc s_Instance;
	protected static const int PENDING_COOLDOWN_MS = 5000;
	protected ref map<string, int> m_LastPendingRequestMs;

	void ShopClaimGuiRpc()
	{
		m_LastPendingRequestMs = new map<string, int>();
	}

	static ShopClaimGuiRpc Get()
	{
		if (!s_Instance)
			s_Instance = new ShopClaimGuiRpc();
		return s_Instance;
	}

	void InitServer()
	{
		GetRPCManager().AddRPC(SC_RPC_MOD, SC_RPC_REQUEST_PENDING_LIST, this, SingleplayerExecutionType.Server);
		GetRPCManager().AddRPC(SC_RPC_MOD, SC_RPC_CLAIM, this, SingleplayerExecutionType.Server);
		GetRPCManager().AddRPC(SC_RPC_MOD, SC_RPC_RESPAWN_CONTAINER, this, SingleplayerExecutionType.Server);
		ShopClaimLogger.Info("ShopClaimGuiRpc server handlers registered");
	}

	void RequestPendingList(CallType type, ParamsReadContext ctx, PlayerIdentity sender, Object target)
	{
		if (type != CallType.Server)
			return;

		PlayerBase player = FindPlayerByIdentity(sender);
		if (!player || !sender)
			return;

		string steamId = sender.GetPlainId();
		int now = GetGame().GetTime();

		if (m_LastPendingRequestMs.Contains(steamId))
		{
			int last = m_LastPendingRequestMs.Get(steamId);
			if (now - last < PENDING_COOLDOWN_MS)
			{
				ShopClaimModConfig cfg = ShopClaimSettings.Get();
				string waitMsg = "Подождите…";
				if (cfg && cfg.messages)
					waitMsg = cfg.messages.please_wait;
				SendSyncPendingError(sender, waitMsg);
				return;
			}
		}

		m_LastPendingRequestMs.Set(steamId, now);
		ShopClaimHttpClient.Get().RequestPendingListForGui(player);
	}

	void Claim(CallType type, ParamsReadContext ctx, PlayerIdentity sender, Object target)
	{
		if (type != CallType.Server)
			return;

		Param1<string> data;
		if (!ctx.Read(data))
			return;

		PlayerBase player = FindPlayerByIdentity(sender);
		if (!player || !sender)
			return;

		string steamId = sender.GetPlainId();
		string operationId = data.param1;

		if (!operationId || operationId == "")
		{
			SendClaimResult(sender, false, ResolveListStaleMessage(), false);
			return;
		}

		ShopClaimHttpClient.Get().RequestClaimByOperationId(player, operationId, ShopClaimNotifyChannel.GUI);
	}

	void RespawnContainer(CallType type, ParamsReadContext ctx, PlayerIdentity sender, Object target)
	{
		if (type != CallType.Server)
			return;

		PlayerBase player = FindPlayerByIdentity(sender);
		if (!player || !sender)
			return;

		ShopClaimService.Get().RespawnContainer(player, ShopClaimNotifyChannel.GUI);
	}

	void SendSyncPendingList(PlayerIdentity identity, array<ref ShopClaimPendingOrder> orders)
	{
		if (!identity)
			return;

		string steamId = identity.GetPlainId();
		string activeOpId = ShopClaimContainerTracker.Get().GetActiveOperationId(steamId);
		string json = ShopClaimGuiSerializer.SerializePendingEnvelope(orders, activeOpId, ShopClaimSettings.GetThemePrefix());
		GetRPCManager().SendRPC(SC_RPC_MOD, SC_RPC_SYNC_PENDING_LIST, new Param1<string>(json), true, identity);
	}

	void SendSyncPendingError(PlayerIdentity identity, string message)
	{
		if (!identity)
			return;

		if (!message || message == "")
			message = "Ошибка загрузки списка.";

		string json = ShopClaimGuiSerializer.SerializeErrorEnvelope(message, ShopClaimSettings.GetThemePrefix());
		GetRPCManager().SendRPC(SC_RPC_MOD, SC_RPC_SYNC_PENDING_ERROR, new Param1<string>(json), true, identity);
	}

	void SendClaimResult(PlayerBase player, bool ok, string message, bool closeMenu)
	{
		if (!player || !player.GetIdentity())
			return;

		SendClaimResult(player.GetIdentity(), ok, message, closeMenu);
	}

	void SendClaimResult(PlayerIdentity identity, bool ok, string message, bool closeMenu)
	{
		if (!identity)
			return;

		if (!message)
			message = "";

		GetRPCManager().SendRPC(SC_RPC_MOD, SC_RPC_CLAIM_RESULT, new Param3<bool, string, bool>(ok, message, closeMenu), true, identity);
	}

	protected static string ResolveListStaleMessage()
	{
		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (cfg && cfg.messages && cfg.messages.list_stale != "")
			return cfg.messages.list_stale;

		return "Обновите список покупок.";
	}

	protected static PlayerBase FindPlayerByIdentity(PlayerIdentity identity)
	{
		if (!identity)
			return null;

		array<Man> players = new array<Man>();
		GetGame().GetPlayers(players);

		foreach (Man man : players)
		{
			PlayerBase player = PlayerBase.Cast(man);
			if (!player || !player.GetIdentity())
				continue;

			if (player.GetIdentity().GetId() == identity.GetId())
				return player;
		}

		return null;
	}
};
