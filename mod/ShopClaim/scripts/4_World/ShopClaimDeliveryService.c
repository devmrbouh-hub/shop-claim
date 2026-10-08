class ShopClaimService
{
	protected static ref ShopClaimService s_Instance;
	protected ref map<string, int> m_LastRespawnMs;
	protected string m_SurfaceBlockedSteamId;

	void ShopClaimService()
	{
		m_LastRespawnMs = new map<string, int>();
	}

	static ShopClaimService Get()
	{
		if (!s_Instance)
			s_Instance = new ShopClaimService();
		return s_Instance;
	}

	void TryClaim(PlayerBase player, ShopClaimPendingOrder order, ShopClaimNotifyChannel channel)
	{
		if (!player || !player.GetIdentity() || !order)
			return;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg || !cfg.messages)
			return;

		string steamId = player.GetIdentity().GetPlainId();

		if (order.IsVehicle())
		{
			TryClaimVehicle(player, order, cfg, steamId, channel);
			return;
		}

		TryClaimContainer(player, order, cfg, steamId, channel);
	}

	void RespawnContainer(PlayerBase player, ShopClaimNotifyChannel channel)
	{
		if (!player || !player.GetIdentity())
			return;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg || !cfg.messages)
			return;

		string steamId = player.GetIdentity().GetPlainId();
		ShopClaimContainerTracker tracker = ShopClaimContainerTracker.Get();

		if (!tracker.HasActiveContainer(steamId))
		{
			NotifyError(player, channel, cfg.messages.container_respawn_none, false);
			return;
		}

		if (!CheckRespawnCooldown(steamId, cfg))
		{
			NotifyError(player, channel, cfg.messages.please_wait, false);
			return;
		}

		string operationId = tracker.GetActiveOperationId(steamId);
		EntityAI existing = tracker.GetActiveContainerEntity(steamId);
		if (!operationId || operationId == "" || !existing)
		{
			NotifyError(player, channel, cfg.messages.container_respawn_none, false);
			return;
		}

		ShopClaimFulfillmentWorld.ReconcileFromCargo(operationId, existing);

		if (!ShopClaimFulfillmentStore.Get().HasRemaining(operationId))
		{
			tracker.UnregisterDelivered(steamId, true);
			ShopClaimHttpClient.Get().PostDelivered(steamId, operationId, player);
			Notify(player, channel, cfg.messages.container_nothing_left, false);
			return;
		}

		string containerClass = tracker.GetStoredContainerClass(steamId);
		tracker.UnregisterOnly(steamId, true);

		EntityAI chest = SpawnContainerAtPlayer(player, containerClass, operationId, steamId, cfg);
		if (!chest)
		{
			if (WasLastSpawnSurfaceBlocked(steamId))
				NotifyError(player, channel, cfg.messages.container_bad_surface, false);
			else
				NotifyError(player, channel, cfg.messages.claim_failed, false);
			return;
		}

		int filled = FillContainerFromLedger(chest, operationId);
		if (filled <= 0)
		{
			chest.Delete();
			ShopClaimFulfillmentStore.Get().RemoveOperation(operationId);
			ShopClaimHttpClient.Get().PostDelivered(steamId, operationId, player);
			Notify(player, channel, cfg.messages.container_nothing_left, false);
			return;
		}

		tracker.Register(steamId, operationId, chest);
		Notify(player, channel, cfg.messages.container_respawn_ok, false);
	}

	protected void TryClaimContainer(PlayerBase player, ShopClaimPendingOrder order, ShopClaimModConfig cfg, string steamId, ShopClaimNotifyChannel channel)
	{
		ShopClaimContainerTracker tracker = ShopClaimContainerTracker.Get();

		if (tracker.HasActiveContainer(steamId))
		{
			NotifyError(player, channel, cfg.messages.container_active, false);
			return;
		}

		bool alreadySpawned = order.IsSpawned();
		if (!order.IsAvailable() && !alreadySpawned)
		{
			NotifyError(player, channel, cfg.messages.claim_failed, false);
			return;
		}

		if (!order.IsContainer())
		{
			NotifyError(player, channel, cfg.messages.claim_failed, false);
			return;
		}

		ShopClaimFulfillmentStore fulfillment = ShopClaimFulfillmentStore.Get();
		bool hasLedger = fulfillment.HasOperation(order.operation_id);

		if (alreadySpawned && !hasLedger)
		{
			ShopClaimLogger.Error("alreadySpawned without ledger op=" + order.operation_id + " steam=" + steamId);
			NotifyError(player, channel, cfg.messages.claim_failed, false);
			return;
		}

		if (!hasLedger)
			fulfillment.InitFromOrder(order.operation_id, order.delivery.Items);

		if (!fulfillment.HasRemaining(order.operation_id))
		{
			ShopClaimFulfillmentStore.Get().RemoveOperation(order.operation_id);
			ShopClaimHttpClient.Get().PostDelivered(steamId, order.operation_id, player);
			Notify(player, channel, cfg.messages.container_nothing_left, false);
			return;
		}

		if (alreadySpawned)
			ShopClaimLogger.Info("Recovering spawned order without active container: " + order.operation_id);

		string containerClass = ResolveContainerClass(order, cfg);
		EntityAI chest = SpawnContainerAtPlayer(player, containerClass, order.operation_id, steamId, cfg);
		if (!chest)
		{
			if (WasLastSpawnSurfaceBlocked(steamId))
				NotifyError(player, channel, cfg.messages.container_bad_surface, false);
			else
				NotifyError(player, channel, cfg.messages.claim_failed, false);
			return;
		}

		int filled = FillContainerFromLedger(chest, order.operation_id);
		if (filled <= 0)
		{
			chest.Delete();
			ShopClaimFulfillmentStore.Get().RemoveOperation(order.operation_id);
			ShopClaimHttpClient.Get().PostDelivered(steamId, order.operation_id, player);
			Notify(player, channel, cfg.messages.container_nothing_left, false);
			return;
		}

		tracker.Register(steamId, order.operation_id, chest);

		if (!alreadySpawned)
		{
			ShopClaimClaimContext.Set(steamId, order.operation_id, channel);
			ShopClaimHttpClient.Get().PostSpawned(player, order.operation_id);
		}
		else
		{
			Notify(player, channel, cfg.messages.delivered_container, false);
		}
	}

	protected void TryClaimVehicle(PlayerBase player, ShopClaimPendingOrder order, ShopClaimModConfig cfg, string steamId, ShopClaimNotifyChannel channel)
	{
		if (!order.IsAvailable())
		{
			NotifyError(player, channel, cfg.messages.claim_failed, false);
			return;
		}

		if (ShopClaimClaimGuard.Get().IsLocked(steamId) || ShopClaimHttpClient.Get().IsBusy())
		{
			NotifyError(player, channel, cfg.messages.please_wait, false);
			return;
		}

		if (!ShopClaimClaimGuard.Get().TryAcquire(steamId))
		{
			NotifyError(player, channel, cfg.messages.please_wait, false);
			return;
		}

		Car vehicle;
		if (!ShopClaimVehicleSpawner.Get().TrySpawn(player, order, vehicle))
		{
			ShopClaimClaimGuard.Get().Release(steamId);

			if (ShopClaimVehicleSpawner.Get().WasCooldownBlocked(steamId))
				NotifyError(player, channel, cfg.messages.please_wait, false);
			else
				NotifyError(player, channel, cfg.messages.vehicle_no_space, false);

			return;
		}

		ShopClaimClaimGuard.Get().SetPendingVehicle(steamId, order.operation_id, vehicle);
		ShopClaimClaimContext.Set(steamId, order.operation_id, channel);
		ShopClaimHttpClient.Get().PostDelivered(steamId, order.operation_id, player);
	}

	protected bool WasLastSpawnSurfaceBlocked(string steamId)
	{
		if (!steamId || steamId == "")
			return false;

		return m_SurfaceBlockedSteamId == steamId;
	}

	protected bool CheckRespawnCooldown(string steamId, ShopClaimModConfig cfg)
	{
		if (!steamId || steamId == "")
			return true;

		int now = GetGame().GetTime();
		int cooldownMs = cfg.container_respawn_cooldown_sec * 1000;
		if (cooldownMs < 1000)
			cooldownMs = 30000;

		if (m_LastRespawnMs.Contains(steamId))
		{
			int last = m_LastRespawnMs.Get(steamId);
			if (now - last < cooldownMs)
				return false;
		}

		m_LastRespawnMs.Set(steamId, now);
		return true;
	}

	protected void Notify(PlayerBase player, ShopClaimNotifyChannel channel, string message, bool closeMenu)
	{
		if (!player || !player.GetIdentity())
			return;

		if (channel == ShopClaimNotifyChannel.GUI)
			ShopClaimGuiRpc.Get().SendClaimResult(player, true, message, closeMenu);
		else
			ShopClaimPlayerMessenger.Send(player, message);
	}

	protected void NotifyError(PlayerBase player, ShopClaimNotifyChannel channel, string message, bool closeMenu)
	{
		if (!player || !player.GetIdentity())
			return;

		if (channel == ShopClaimNotifyChannel.GUI)
			ShopClaimGuiRpc.Get().SendClaimResult(player, false, message, closeMenu);
		else
			ShopClaimPlayerMessenger.Send(player, message);
	}

	protected string ResolveContainerClass(ShopClaimPendingOrder order, ShopClaimModConfig cfg)
	{
		if (order && order.delivery && order.delivery.Container != "")
			return order.delivery.Container;

		if (cfg && cfg.container_class != "")
			return cfg.container_class;

		return "SeaChest";
	}

	protected EntityAI SpawnContainerAtPlayer(PlayerBase player, string className, string operationId, string steamId, ShopClaimModConfig cfg)
	{
		m_SurfaceBlockedSteamId = "";

		if (!player || !className || className == "")
			return null;

		ref ShopClaimSpawnSurfaceParams params = new ShopClaimSpawnSurfaceParams();
		if (cfg)
		{
			if (cfg.container_spawn_distance_m > 0)
				params.DistanceM = cfg.container_spawn_distance_m;
			if (cfg.container_spawn_max_slope_deg > 0)
				params.MaxSlopeDeg = cfg.container_spawn_max_slope_deg;
			if (cfg.container_spawn_check_radius_m > 0)
				params.CheckRadiusM = cfg.container_spawn_check_radius_m;
		}

		vector spawnPos;
		if (!ShopClaimSpawnSurface.FindPositionNearPlayer(player, params, spawnPos))
		{
			m_SurfaceBlockedSteamId = steamId;
			ShopClaimLogger.Info("Container spawn blocked by surface op=" + operationId);
			return null;
		}

		Object obj = GetGame().CreateObjectEx(className, spawnPos, ECE_PLACE_ON_SURFACE);
		EntityAI chest = EntityAI.Cast(obj);
		if (!chest)
		{
			ShopClaimLogger.Error("Failed to spawn container class=" + className + " op=" + operationId);
			if (obj)
				obj.Delete();
			return null;
		}

		chest.SetOrientation(player.GetOrientation());

		Container_Base wargmContainer = Container_Base.Cast(chest);
		if (wargmContainer)
			wargmContainer.ShopClaimMark(steamId, operationId);
		else
			ShopClaimLogger.Error("Container class is not Container_Base: " + className + " op=" + operationId);

		ShopClaimLogger.Info("Spawned " + className + " at " + spawnPos.ToString() + " op=" + operationId);
		return chest;
	}

	protected int FillContainerFromLedger(EntityAI chest, string operationId)
	{
		if (!chest || !chest.GetInventory() || !operationId || operationId == "")
			return 0;

		array<ref ShopClaimFulfillmentLine> lines = ShopClaimFulfillmentStore.Get().GetLines(operationId);
		if (!lines)
			return 0;

		Container_Base wargmContainer = Container_Base.Cast(chest);
		if (wargmContainer)
			wargmContainer.ShopClaimBeginFill();

		int filled = 0;
		foreach (ShopClaimFulfillmentLine line : lines)
		{
			if (!line || line.qty_remaining <= 0)
				continue;

			for (int i = 0; i < line.qty_remaining; i++)
			{
				EntityAI created = chest.GetInventory().CreateInInventory(line.class_name);
				if (!created)
				{
					ShopClaimLogger.Error("Failed to create item " + line.class_name + " op=" + operationId);
					continue;
				}

				filled++;

				if (line.attachments)
				{
					foreach (string attachment : line.attachments)
					{
						if (attachment == "")
							continue;
						created.GetInventory().CreateAttachment(attachment);
					}
				}
			}
		}

		if (wargmContainer)
			wargmContainer.ShopClaimEndFill();

		ShopClaimLogger.Info("Container filled from ledger items=" + filled.ToString() + " op=" + operationId);
		return filled;
	}
};
