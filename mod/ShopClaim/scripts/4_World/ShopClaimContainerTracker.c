class ShopClaimActiveContainer
{
	string SteamId;
	string OperationId;
	EntityAI Container;
};

class ShopClaimContainerTracker
{
	protected static ref ShopClaimContainerTracker s_Instance;
	protected ref map<string, ref ShopClaimActiveContainer> m_ActiveBySteam;
	protected ref ShopClaimContainerStore m_Store;
	protected bool m_TimerRunning;

	void ShopClaimContainerTracker()
	{
		m_ActiveBySteam = new map<string, ref ShopClaimActiveContainer>();
		m_Store = new ShopClaimContainerStore();
	}

	static ShopClaimContainerTracker Get()
	{
		if (!s_Instance)
			s_Instance = new ShopClaimContainerTracker();
		return s_Instance;
	}

	void LoadPendingFromStore()
	{
		m_Store.Load();
	}

	void RestoreTimeout()
	{
		array<ref ShopClaimStoredContainer> entries = m_Store.GetAll();
		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		int abandonedMinutes = 24 * 60;
		if (cfg && cfg.abandoned_container_hours > 0)
			abandonedMinutes = cfg.abandoned_container_hours * 60;

		foreach (ref ShopClaimStoredContainer entry : entries)
		{
			if (!entry || entry.steam_id == "")
				continue;

			string steamId = entry.steam_id;
			bool linked = m_ActiveBySteam.Contains(steamId);
			if (linked)
			{
				ref ShopClaimActiveContainer active = m_ActiveBySteam.Get(steamId);
				if (active && active.Container && active.Container.IsAlive())
				{
					if (entry.spawned_minutes > 0 && ShopClaimTimeHelper.MinutesSince(entry.spawned_minutes) >= abandonedMinutes)
					{
						ShopClaimLogger.Info("Abandoned container purge op=" + entry.operation_id);
						Unregister(steamId, true, true);
					}
					continue;
				}
			}

			ShopClaimLogger.Info("RestoreTimeout: pending without entity steam=" + steamId + " op=" + entry.operation_id);
			m_Store.Remove(steamId);
		}
	}

	bool HasActiveContainer(string steamId)
	{
		if (m_Store.Has(steamId))
			return true;

		PurgeStale(steamId);

		if (!m_ActiveBySteam.Contains(steamId))
			return false;

		ref ShopClaimActiveContainer active = m_ActiveBySteam.Get(steamId);
		if (!active || !active.Container || !active.Container.IsAlive())
		{
			Unregister(steamId, false, true);
			return false;
		}

		return true;
	}

	string GetActiveOperationId(string steamId)
	{
		if (m_Store.Has(steamId))
		{
			ref ShopClaimStoredContainer stored = m_Store.Get(steamId);
			if (stored)
				return stored.operation_id;
		}

		PurgeStale(steamId);
		if (!m_ActiveBySteam.Contains(steamId))
			return "";

		ref ShopClaimActiveContainer active = m_ActiveBySteam.Get(steamId);
		if (!active)
			return "";

		return active.OperationId;
	}

	EntityAI GetActiveContainerEntity(string steamId)
	{
		PurgeStale(steamId);
		if (!m_ActiveBySteam.Contains(steamId))
			return null;

		ref ShopClaimActiveContainer active = m_ActiveBySteam.Get(steamId);
		if (!active || !active.Container || !active.Container.IsAlive())
			return null;

		return active.Container;
	}

	string GetStoredContainerClass(string steamId)
	{
		ref ShopClaimStoredContainer stored = m_Store.Get(steamId);
		if (stored && stored.container_class != "")
			return stored.container_class;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (cfg && cfg.container_class != "")
			return cfg.container_class;

		return "SeaChest";
	}

	void UnregisterOnly(string steamId, bool deleteEntity)
	{
		Unregister(steamId, deleteEntity, true);
	}

	void UnregisterDelivered(string steamId, bool deleteEntity)
	{
		string operationId = GetActiveOperationId(steamId);
		Unregister(steamId, deleteEntity, true);

		if (operationId && operationId != "")
			ShopClaimFulfillmentStore.Get().RemoveOperation(operationId);
	}

	protected void PurgeStale(string steamId)
	{
		if (!m_ActiveBySteam.Contains(steamId))
			return;

		ref ShopClaimActiveContainer active = m_ActiveBySteam.Get(steamId);
		if (!active)
		{
			m_ActiveBySteam.Remove(steamId);
			return;
		}

		if (!active.Container || !active.Container.IsAlive())
		{
			ShopClaimLogger.Info("Purged dead container op=" + active.OperationId);
			Unregister(steamId, false, true);
			return;
		}

		if (!active.Container.GetInventory() || !active.Container.GetInventory().GetCargo())
		{
			ShopClaimLogger.Info("Purged invalid container op=" + active.OperationId);
			Unregister(steamId, true, true);
		}
	}

	void Register(string steamId, string operationId, EntityAI container)
	{
		RegisterInternal(steamId, operationId, container, false);
	}

	void RegisterSelf(string steamId, string operationId, EntityAI container)
	{
		RegisterInternal(steamId, operationId, container, true);
	}

	protected void RegisterInternal(string steamId, string operationId, EntityAI container, bool fromPersistence)
	{
		if (!steamId || steamId == "" || !operationId || operationId == "" || !container)
			return;

		ref ShopClaimActiveContainer active = new ShopClaimActiveContainer();
		active.SteamId = steamId;
		active.OperationId = operationId;
		active.Container = container;
		m_ActiveBySteam.Set(steamId, active);

		int pid1, pid2, pid3, pid4;
		TryGetPersistentId(container, pid1, pid2, pid3, pid4);
		m_Store.Upsert(steamId, operationId, container.GetType(), pid1, pid2, pid3, pid4);

		if (fromPersistence)
		{
			ShopClaimLogger.Info("RegisterSelf op=" + operationId + " steam=" + steamId);
			ShopClaimFulfillmentWorld.ReconcileFromCargo(operationId, container);
		}
		else
		{
			ShopClaimLogger.Info("Register op=" + operationId + " steam=" + steamId);
		}

		EnsureTimer();
	}

	void Clear(string steamId)
	{
		Unregister(steamId, true, true);
	}

	protected void Unregister(string steamId, bool deleteEntity, bool removeFromStore)
	{
		if (m_ActiveBySteam.Contains(steamId))
		{
			ref ShopClaimActiveContainer active = m_ActiveBySteam.Get(steamId);
			if (deleteEntity && active && active.Container && active.Container.IsAlive())
				active.Container.Delete();

			m_ActiveBySteam.Remove(steamId);
		}

		if (removeFromStore)
			m_Store.Remove(steamId);
	}

	void Start()
	{
		EnsureTimer();
	}

	protected void EnsureTimer()
	{
		if (m_TimerRunning)
			return;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		int intervalMs = 5000;
		if (cfg)
			intervalMs = cfg.container_empty_check_sec * 1000;

		m_TimerRunning = true;
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(Tick, intervalMs, true);
	}

	protected void Tick()
	{
		SyncPersistentIds();

		if (m_ActiveBySteam.Count() == 0)
			return;

		array<string> keys = m_ActiveBySteam.GetKeyArray();
		foreach (string steamId : keys)
		{
			ref ShopClaimActiveContainer active = m_ActiveBySteam.Get(steamId);
			if (!active || !active.Container)
			{
				Unregister(steamId, false, true);
				continue;
			}

			if (!active.Container.IsAlive())
			{
				Unregister(steamId, false, true);
				continue;
			}

			if (!IsCargoEmpty(active.Container))
				continue;

			string operationId = active.OperationId;
			UnregisterDelivered(steamId, true);

			PlayerBase player = FindOnlinePlayer(steamId);
			ShopClaimHttpClient.Get().PostDelivered(steamId, operationId, player);
		}
	}

	protected void SyncPersistentIds()
	{
		array<string> keys = m_ActiveBySteam.GetKeyArray();
		foreach (string steamId : keys)
		{
			ref ShopClaimActiveContainer active = m_ActiveBySteam.Get(steamId);
			if (!active || !active.Container || !active.Container.IsAlive())
				continue;

			ref ShopClaimStoredContainer stored = m_Store.Get(steamId);
			if (stored && stored.pid1 != 0 && stored.pid2 != 0)
				continue;

			int pid1, pid2, pid3, pid4;
			if (!TryGetPersistentId(active.Container, pid1, pid2, pid3, pid4))
				continue;

			m_Store.UpdatePersistentIds(steamId, pid1, pid2, pid3, pid4);
		}
	}

	protected bool TryGetPersistentId(EntityAI entity, out int pid1, out int pid2, out int pid3, out int pid4)
	{
		pid1 = 0;
		pid2 = 0;
		pid3 = 0;
		pid4 = 0;

		if (!entity)
			return false;

		entity.GetPersistentID(pid1, pid2, pid3, pid4);
		return pid1 != 0 || pid2 != 0 || pid3 != 0 || pid4 != 0;
	}

	protected bool IsCargoEmpty(EntityAI entity)
	{
		if (!entity || !entity.GetInventory())
			return true;

		CargoBase cargo = entity.GetInventory().GetCargo();
		if (!cargo)
			return true;

		return cargo.GetItemCount() == 0;
	}

	protected PlayerBase FindOnlinePlayer(string steamId)
	{
		array<Man> players = new array<Man>();
		GetGame().GetPlayers(players);

		foreach (Man man : players)
		{
			PlayerBase player = PlayerBase.Cast(man);
			if (!player || !player.GetIdentity())
				continue;

			if (player.GetIdentity().GetPlainId() == steamId)
				return player;
		}

		return null;
	}
};
