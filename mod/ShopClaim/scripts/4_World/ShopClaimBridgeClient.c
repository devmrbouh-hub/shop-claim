enum ShopClaimHttpRequestType
{
	PENDING_LIST,
	MARK_SPAWNED,
	MARK_DELIVERED
};

class ShopClaimHttpRequest
{
	ShopClaimHttpRequestType Type;
	PlayerBase Player;
	string SteamId;
	string OperationId;
	ShopClaimNotifyChannel ListChannel;
	ShopClaimNotifyChannel NotifyChannel;
};

class ShopClaimHttpCallback : RestCallback
{
	override void OnError(int errorCode)
	{
		ShopClaimHttpClient.OnHttpError(errorCode);
	}

	override void OnTimeout()
	{
		ShopClaimHttpClient.OnHttpError(-1);
	}

	override void OnSuccess(string data, int dataSize)
	{
		ShopClaimHttpClient.OnHttpSuccess(data);
	}
};

class ShopClaimHttpClient
{
	protected static ref ShopClaimHttpClient s_Instance;
	protected ref ShopClaimHttpCallback m_Callback;
	protected ref ShopClaimHttpRequest m_ActiveRequest;
	protected ref ShopClaimPendingCache m_Cache;
	protected bool m_Busy;

	void ShopClaimHttpClient()
	{
		m_Callback = new ShopClaimHttpCallback();
		m_Cache = new ShopClaimPendingCache();
		m_Busy = false;
	}

	static ShopClaimHttpClient Get()
	{
		if (!s_Instance)
			s_Instance = new ShopClaimHttpClient();
		return s_Instance;
	}

	ShopClaimPendingCache GetCache()
	{
		return m_Cache;
	}

	bool IsBusy()
	{
		return m_Busy;
	}

	void RequestPendingList(PlayerBase player)
	{
		RequestPendingListInternal(player, ShopClaimNotifyChannel.CHAT);
	}

	void RequestPendingListForGui(PlayerBase player)
	{
		RequestPendingListInternal(player, ShopClaimNotifyChannel.GUI);
	}

	protected void RequestPendingListInternal(PlayerBase player, ShopClaimNotifyChannel channel)
	{
		if (!player || !player.GetIdentity())
			return;

		if (m_Busy)
		{
			NotifyPleaseWait(player, channel);
			return;
		}

		ref ShopClaimHttpRequest req = new ShopClaimHttpRequest();
		req.Type = ShopClaimHttpRequestType.PENDING_LIST;
		req.Player = player;
		req.SteamId = player.GetIdentity().GetPlainId();
		req.ListChannel = channel;
		SendRequest(req);
	}

	void RequestClaimByIndex(PlayerBase player, int index1Based)
	{
		if (!player || !player.GetIdentity())
			return;

		if (m_Busy)
		{
			ShopClaimPlayerMessenger.Send(player, ShopClaimSettings.Get().messages.please_wait);
			return;
		}

		string steamId = player.GetIdentity().GetPlainId();

		if (ShopClaimClaimGuard.Get().IsLocked(steamId))
		{
			ShopClaimPlayerMessenger.Send(player, ShopClaimSettings.Get().messages.please_wait);
			return;
		}

		ShopClaimPendingOrder order = m_Cache.GetByIndex(steamId, index1Based);
		if (!order)
		{
			ShopClaimPlayerMessenger.Send(player, ShopClaimSettings.Get().messages.invalid_index);
			return;
		}

		ShopClaimService.Get().TryClaim(player, order, ShopClaimNotifyChannel.CHAT);
	}

	void RequestClaimByOperationId(PlayerBase player, string operationId, ShopClaimNotifyChannel channel)
	{
		if (!player || !player.GetIdentity())
			return;

		PlayerIdentity identity = player.GetIdentity();
		string steamId = identity.GetPlainId();

		if (m_Busy)
		{
			NotifyPleaseWait(player, channel);
			return;
		}

		if (ShopClaimClaimGuard.Get().IsLocked(steamId))
		{
			NotifyPleaseWait(player, channel);
			return;
		}

		ShopClaimPendingOrder order = m_Cache.GetByOperationId(steamId, operationId);
		if (!order)
		{
			if (channel == ShopClaimNotifyChannel.GUI)
			{
				ShopClaimModConfig cfg = ShopClaimSettings.Get();
				string msg = "Обновите список покупок.";
				if (cfg && cfg.messages && cfg.messages.list_stale != "")
					msg = cfg.messages.list_stale;
				ShopClaimGuiRpc.Get().SendClaimResult(identity, false, msg, false);
			}
			else
			{
				ShopClaimPlayerMessenger.Send(player, ShopClaimSettings.Get().messages.invalid_index);
			}
			return;
		}

		ShopClaimService.Get().TryClaim(player, order, channel);
	}

	void PostSpawned(PlayerBase player, string operationId)
	{
		if (!player || !player.GetIdentity())
			return;

		string steamId = player.GetIdentity().GetPlainId();

		ref ShopClaimHttpRequest req = new ShopClaimHttpRequest();
		req.Type = ShopClaimHttpRequestType.MARK_SPAWNED;
		req.Player = player;
		req.SteamId = steamId;
		req.OperationId = operationId;

		ShopClaimNotifyChannel channel;
		if (ShopClaimClaimContext.Get(steamId, operationId, channel))
			req.NotifyChannel = channel;
		else
			req.NotifyChannel = ShopClaimNotifyChannel.CHAT;

		SendRequest(req);
	}

	void PostDelivered(string steamId, string operationId, PlayerBase player)
	{
		ref ShopClaimHttpRequest req = new ShopClaimHttpRequest();
		req.Type = ShopClaimHttpRequestType.MARK_DELIVERED;
		req.Player = player;
		req.SteamId = steamId;
		req.OperationId = operationId;

		ShopClaimNotifyChannel channel;
		if (ShopClaimClaimContext.Get(steamId, operationId, channel))
			req.NotifyChannel = channel;
		else
			req.NotifyChannel = ShopClaimNotifyChannel.CHAT;

		SendRequest(req);
	}

	protected static string NormalizeBridgeUrl(string bridgeUrl)
	{
		if (!bridgeUrl || bridgeUrl == "")
			return bridgeUrl;

		int len = bridgeUrl.Length();
		string last = bridgeUrl.Substring(len - 1, 1);
		if (last != "/")
			return bridgeUrl + "/";

		return bridgeUrl;
	}

	protected static string BuildAuthedPath(string path, string apiToken)
	{
		return path + "?api_token=" + apiToken;
	}

	protected void SendRequest(ShopClaimHttpRequest req)
	{
		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg || !cfg.IsValid())
		{
			if (req.Player)
			{
				string msg = "Сервис магазина временно недоступен.";
				if (cfg && cfg.messages)
					msg = cfg.messages.service_unavailable;
				NotifyServiceUnavailable(req.Player, ResolveNotifyChannel(req), msg);
			}
			return;
		}

		m_ActiveRequest = req;
		m_Busy = true;

		RestApi api = GetRestApi();
		if (!api)
			api = CreateRestApi();

		string baseUrl = NormalizeBridgeUrl(cfg.bridge_url);
		RestContext ctx = api.GetRestContext(baseUrl);
		ctx.SetHeader("application/json");

		string path;
		switch (req.Type)
		{
			case ShopClaimHttpRequestType.PENDING_LIST:
				path = BuildAuthedPath("api/v1/servers/" + cfg.server_id + "/players/" + req.SteamId + "/pending", cfg.api_token);
				ShopClaimLogger.Info("GET " + baseUrl + path);
				ctx.GET(m_Callback, path);
				break;

			case ShopClaimHttpRequestType.MARK_SPAWNED:
				path = BuildAuthedPath("api/v1/servers/" + cfg.server_id + "/operations/" + req.OperationId + "/spawned", cfg.api_token);
				ShopClaimLogger.Info("POST " + baseUrl + path);
				ctx.POST(m_Callback, path, "{}");
				break;

			case ShopClaimHttpRequestType.MARK_DELIVERED:
				path = BuildAuthedPath("api/v1/servers/" + cfg.server_id + "/operations/" + req.OperationId + "/delivered", cfg.api_token);
				ShopClaimLogger.Info("POST " + baseUrl + path);
				ctx.POST(m_Callback, path, "{}");
				break;
		}
	}

	static void OnHttpError(int errorCode)
	{
		ShopClaimHttpClient self = Get();
		ref ShopClaimHttpRequest req = self.m_ActiveRequest;
		self.m_Busy = false;
		self.m_ActiveRequest = null;

		ShopClaimLogger.Error("HTTP error code=" + errorCode.ToString());

		if (!req)
			return;

		if (req.Type == ShopClaimHttpRequestType.MARK_DELIVERED && req.SteamId != "")
			ShopClaimClaimGuard.Get().RollbackPending(req.SteamId);

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		string msg = "Сервис магазина временно недоступен.";
		if (cfg && cfg.messages)
			msg = cfg.messages.service_unavailable;

		if (req.Type == ShopClaimHttpRequestType.PENDING_LIST)
		{
			if (req.Player && req.Player.GetIdentity())
				NotifyServiceUnavailable(req.Player, req.ListChannel, msg);
			return;
		}

		if (req.Type == ShopClaimHttpRequestType.MARK_SPAWNED || req.Type == ShopClaimHttpRequestType.MARK_DELIVERED)
		{
			if (req.SteamId != "" && req.OperationId != "")
				ShopClaimClaimContext.Take(req.SteamId, req.OperationId, req.NotifyChannel);

			if (req.Player && req.Player.GetIdentity())
			{
				if (req.NotifyChannel == ShopClaimNotifyChannel.GUI)
					ShopClaimGuiRpc.Get().SendClaimResult(req.Player, false, msg, false);
				else
					ShopClaimPlayerMessenger.Send(req.Player, msg);
			}
		}
	}

	static void OnHttpSuccess(string data)
	{
		ShopClaimHttpClient self = Get();
		ref ShopClaimHttpRequest req = self.m_ActiveRequest;
		self.m_Busy = false;
		self.m_ActiveRequest = null;

		if (!req)
			return;

		switch (req.Type)
		{
			case ShopClaimHttpRequestType.PENDING_LIST:
				self.HandlePendingList(req, data);
				break;

			case ShopClaimHttpRequestType.MARK_SPAWNED:
				self.HandleMarkSpawned(req);
				break;

			case ShopClaimHttpRequestType.MARK_DELIVERED:
				self.HandleMarkDelivered(req);
				break;
		}
	}

	protected void HandlePendingList(ShopClaimHttpRequest req, string data)
	{
		array<ref ShopClaimPendingOrder> orders;
		ShopClaimJsonHelper.ParsePendingOrders(data, orders);

		m_Cache.Store(req.SteamId, orders);

		if (!req.Player || !req.Player.GetIdentity())
			return;

		if (req.ListChannel == ShopClaimNotifyChannel.GUI)
			ShopClaimGuiRpc.Get().SendSyncPendingList(req.Player.GetIdentity(), orders);
		else
			ShopClaimOrderPresenter.SendOrderList(req.Player, orders);
	}

	protected void HandleMarkSpawned(ShopClaimHttpRequest req)
	{
		ShopClaimNotifyChannel channel = req.NotifyChannel;
		if (req.SteamId != "" && req.OperationId != "")
			ShopClaimClaimContext.Take(req.SteamId, req.OperationId, channel);

		if (!req.Player || !req.Player.GetIdentity())
			return;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg || !cfg.messages)
			return;

		if (channel == ShopClaimNotifyChannel.GUI)
			ShopClaimGuiRpc.Get().SendClaimResult(req.Player, true, cfg.messages.delivered_container, false);
		else
			ShopClaimPlayerMessenger.Send(req.Player, cfg.messages.delivered_container);
	}

	protected void HandleMarkDelivered(ShopClaimHttpRequest req)
	{
		ShopClaimLogger.Info("Order delivered: " + req.OperationId);

		bool wasVehicle = ShopClaimClaimGuard.Get().HasPendingVehicle(req.SteamId);
		if (wasVehicle)
			ShopClaimClaimGuard.Get().Release(req.SteamId);

		m_Cache.RemoveOrder(req.SteamId, req.OperationId);

		ShopClaimNotifyChannel channel = req.NotifyChannel;
		if (req.SteamId != "" && req.OperationId != "")
			ShopClaimClaimContext.Take(req.SteamId, req.OperationId, channel);

		if (!req.Player || !req.Player.GetIdentity())
			return;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg || !cfg.messages)
			return;

		if (channel == ShopClaimNotifyChannel.GUI)
		{
			string msg = cfg.messages.delivered_vehicle;
			if (!wasVehicle)
				msg = cfg.messages.delivered_container;
			ShopClaimGuiRpc.Get().SendClaimResult(req.Player, true, msg, true);
		}
		else if (wasVehicle)
		{
			ShopClaimPlayerMessenger.Send(req.Player, cfg.messages.delivered_vehicle);
		}
	}

	protected static ShopClaimNotifyChannel ResolveNotifyChannel(ShopClaimHttpRequest req)
	{
		if (!req)
			return ShopClaimNotifyChannel.CHAT;

		if (req.Type == ShopClaimHttpRequestType.PENDING_LIST)
			return req.ListChannel;

		return req.NotifyChannel;
	}

	protected static void NotifyPleaseWait(PlayerBase player, ShopClaimNotifyChannel channel)
	{
		if (!player || !player.GetIdentity())
			return;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		string msg = "Подождите…";
		if (cfg && cfg.messages)
			msg = cfg.messages.please_wait;

		if (channel == ShopClaimNotifyChannel.GUI)
			ShopClaimGuiRpc.Get().SendSyncPendingError(player.GetIdentity(), msg);
		else
			ShopClaimPlayerMessenger.Send(player, msg);
	}

	protected static void NotifyServiceUnavailable(PlayerBase player, ShopClaimNotifyChannel channel, string msg)
	{
		if (!player || !player.GetIdentity())
			return;

		if (channel == ShopClaimNotifyChannel.GUI)
		{
			if (msg == "")
			{
				ShopClaimModConfig cfg = ShopClaimSettings.Get();
				if (cfg && cfg.messages)
					msg = cfg.messages.service_unavailable;
			}
			ShopClaimGuiRpc.Get().SendSyncPendingError(player.GetIdentity(), msg);
		}
		else
		{
			ShopClaimPlayerMessenger.Send(player, msg);
		}
	}
};
