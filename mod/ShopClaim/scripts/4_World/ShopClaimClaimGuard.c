class ShopClaimPendingVehicleClaim
{
	string OperationId;
	Car Vehicle;
};

class ShopClaimClaimGuard
{
	protected static ref ShopClaimClaimGuard s_Instance;
	protected ref map<string, bool> m_Locks;
	protected ref map<string, ref ShopClaimPendingVehicleClaim> m_Pending;

	void ShopClaimClaimGuard()
	{
		m_Locks = new map<string, bool>();
		m_Pending = new map<string, ref ShopClaimPendingVehicleClaim>();
	}

	static ShopClaimClaimGuard Get()
	{
		if (!s_Instance)
			s_Instance = new ShopClaimClaimGuard();
		return s_Instance;
	}

	bool IsLocked(string steamId)
	{
		if (!steamId || steamId == "")
			return false;

		if (!m_Locks.Contains(steamId))
			return false;

		return m_Locks.Get(steamId);
	}

	bool TryAcquire(string steamId)
	{
		if (!steamId || steamId == "")
			return false;

		if (IsLocked(steamId))
			return false;

		m_Locks.Set(steamId, true);
		return true;
	}

	void Release(string steamId)
	{
		if (!steamId || steamId == "")
			return;

		m_Locks.Set(steamId, false);
		m_Pending.Remove(steamId);
	}

	void SetPendingVehicle(string steamId, string operationId, Car vehicle)
	{
		if (!steamId || steamId == "" || !vehicle)
			return;

		ref ShopClaimPendingVehicleClaim pending = new ShopClaimPendingVehicleClaim();
		pending.OperationId = operationId;
		pending.Vehicle = vehicle;
		m_Pending.Set(steamId, pending);
	}

	bool HasPendingVehicle(string steamId)
	{
		return m_Pending.Contains(steamId) && m_Pending.Get(steamId) != null;
	}

	void RollbackPending(string steamId)
	{
		if (!m_Pending.Contains(steamId))
		{
			Release(steamId);
			return;
		}

		ref ShopClaimPendingVehicleClaim pending = m_Pending.Get(steamId);
		if (pending && pending.Vehicle)
		{
			ShopClaimLogger.Info("Rolling back vehicle spawn op=" + pending.OperationId);
			pending.Vehicle.Delete();
		}

		Release(steamId);
	}
};
