class ShopClaimVehicleSpawner
{
	protected static ref ShopClaimVehicleSpawner s_Instance;
	protected ref map<string, int> m_LastAttemptMs;
	protected string m_CooldownBlockedSteamId;

	void ShopClaimVehicleSpawner()
	{
		m_LastAttemptMs = new map<string, int>();
		m_CooldownBlockedSteamId = "";
	}

	static ShopClaimVehicleSpawner Get()
	{
		if (!s_Instance)
			s_Instance = new ShopClaimVehicleSpawner();
		return s_Instance;
	}

	bool TrySpawn(PlayerBase player, ShopClaimPendingOrder order, out Car vehicle)
	{
		vehicle = null;
		m_CooldownBlockedSteamId = "";

		if (!player || !order || !order.vehicle)
			return false;

		ShopClaimModConfig cfg = ShopClaimSettings.Get();
		if (!cfg)
			return false;

		string steamId = "";
		if (player.GetIdentity())
			steamId = player.GetIdentity().GetPlainId();

		if (!CheckCooldown(steamId, cfg))
			return false;

		ShopClaimVehicleDelivery delivery = order.vehicle;
		if (!delivery.ClassName || delivery.ClassName == "")
		{
			ShopClaimLogger.Error("Vehicle delivery missing class op=" + order.operation_id);
			return false;
		}

		vector spawnPos;
		if (!FindSpawnPosition(player, delivery, spawnPos))
			return false;

		Object obj = GetGame().CreateObjectEx(delivery.ClassName, spawnPos, ECE_PLACE_ON_SURFACE);
		vehicle = Car.Cast(obj);
		if (!vehicle)
		{
			ShopClaimLogger.Error("Failed to spawn vehicle class=" + delivery.ClassName + " op=" + order.operation_id);
			if (obj)
				obj.Delete();
			return false;
		}

		vehicle.SetOrientation(player.GetOrientation());
		ApplySpawnAttachments(vehicle, delivery);
		ApplyFluids(vehicle, delivery);
		ApplyCargoItems(player, vehicle, delivery);

		ShopClaimLogger.Info("Spawned vehicle " + delivery.ClassName + " at " + spawnPos.ToString() + " op=" + order.operation_id);
		return true;
	}

	bool WasCooldownBlocked(string steamId)
	{
		if (!steamId || steamId == "")
			return false;

		return m_CooldownBlockedSteamId == steamId;
	}

	protected bool CheckCooldown(string steamId, ShopClaimModConfig cfg)
	{
		if (!steamId || steamId == "")
			return true;

		int now = GetGame().GetTime();
		int cooldownMs = cfg.vehicle_spawn_cooldown_sec * 1000;
		if (cooldownMs < 1000)
			cooldownMs = 30000;

		if (m_LastAttemptMs.Contains(steamId))
		{
			int last = m_LastAttemptMs.Get(steamId);
			if (now - last < cooldownMs)
			{
				m_CooldownBlockedSteamId = steamId;
				return false;
			}
		}

		m_LastAttemptMs.Set(steamId, now);
		return true;
	}

	protected bool FindSpawnPosition(PlayerBase player, ShopClaimVehicleDelivery delivery, out vector spawnPos)
	{
		spawnPos = "0 0 0";

		ref ShopClaimSpawnSurfaceParams params = new ShopClaimSpawnSurfaceParams();
		params.HeightOffset = 0.2;

		ShopClaimVehicleSpawnConfig spawnCfg = delivery.Spawn;
		if (spawnCfg)
		{
			if (spawnCfg.DistanceM > 0)
				params.DistanceM = spawnCfg.DistanceM;
			if (spawnCfg.MaxSlopeDeg > 0)
				params.MaxSlopeDeg = spawnCfg.MaxSlopeDeg;
			if (spawnCfg.CheckRadiusM > 0)
				params.CheckRadiusM = spawnCfg.CheckRadiusM;
		}

		return ShopClaimSpawnSurface.FindPositionNearPlayer(player, params, spawnPos);
	}

	protected void ApplySpawnAttachments(Car vehicle, ShopClaimVehicleDelivery delivery)
	{
		if (!vehicle || !vehicle.GetInventory() || !delivery.SpawnAttachments)
			return;

		foreach (string attachment : delivery.SpawnAttachments)
		{
			if (!attachment || attachment == "")
				continue;

			EntityAI created = vehicle.GetInventory().CreateAttachment(attachment);
			if (!created)
				ShopClaimLogger.Error("Failed to attach " + attachment + " to vehicle");
		}
	}

	protected void ApplyFluids(Car vehicle, ShopClaimVehicleDelivery delivery)
	{
		if (!vehicle || !delivery)
			return;

		float fuelRatio = delivery.Fuel;
		if (fuelRatio < 0)
			fuelRatio = 1.0;

		float coolantRatio = delivery.Coolant;
		if (coolantRatio < 0)
			coolantRatio = 1.0;

		float capacity = vehicle.GetFluidCapacity(CarFluid.FUEL);
		if (capacity > 0)
			vehicle.Fill(CarFluid.FUEL, capacity * fuelRatio);

		capacity = vehicle.GetFluidCapacity(CarFluid.COOLANT);
		if (capacity > 0)
			vehicle.Fill(CarFluid.COOLANT, capacity * coolantRatio);
	}

	protected void ApplyCargoItems(PlayerBase player, Car vehicle, ShopClaimVehicleDelivery delivery)
	{
		if (!delivery || !delivery.CargoItems)
			return;

		foreach (ShopClaimItem line : delivery.CargoItems)
		{
			if (!line || !line.ClassName || line.ClassName == "")
				continue;

			int qty = line.Qty;
			if (qty < 1)
				qty = 1;

			for (int i = 0; i < qty; i++)
			{
				EntityAI created = null;
				if (vehicle && vehicle.GetInventory())
					created = vehicle.GetInventory().CreateInInventory(line.ClassName);

				if (created)
					continue;

				ShopClaimLogger.Error("Failed to place " + line.ClassName + " in vehicle cargo");

				if (player && player.GetInventory())
				{
					EntityAI playerItem = player.GetInventory().CreateInInventory(line.ClassName);
					if (!playerItem)
						ShopClaimLogger.Error("Failed to place " + line.ClassName + " in player inventory");
				}
			}
		}
	}
};
