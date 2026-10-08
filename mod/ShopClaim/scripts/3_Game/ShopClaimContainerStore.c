class ShopClaimStoredContainer
{
	string steam_id;
	string operation_id;
	string container_class;
	int pid1;
	int pid2;
	int pid3;
	int pid4;
	string spawned_at;
	int spawned_minutes;

	void ShopClaimStoredContainer()
	{
		pid1 = 0;
		pid2 = 0;
		pid3 = 0;
		pid4 = 0;
		spawned_minutes = 0;
	}
};

class ShopClaimActiveContainersFile
{
	int version;
	ref array<ref ShopClaimStoredContainer> containers;

	void ShopClaimActiveContainersFile()
	{
		version = 1;
		containers = new array<ref ShopClaimStoredContainer>();
	}
};

class ShopClaimContainerStore
{
	protected static const string STORE_PATH = "$profile:ShopClaim/active_containers.json";
	protected ref ShopClaimActiveContainersFile m_Data;

	void ShopClaimContainerStore()
	{
		m_Data = new ShopClaimActiveContainersFile();
	}

	void Load()
	{
		m_Data = new ShopClaimActiveContainersFile();

		if (!FileExist(STORE_PATH))
			return;

		JsonFileLoader<ShopClaimActiveContainersFile>.JsonLoadFile(STORE_PATH, m_Data);

		if (!m_Data)
			m_Data = new ShopClaimActiveContainersFile();

		if (!m_Data.containers)
			m_Data.containers = new array<ref ShopClaimStoredContainer>();

		if (m_Data.version < 1)
			m_Data.version = 1;

		ShopClaimLogger.Info("Loaded active_containers count=" + m_Data.containers.Count().ToString());
	}

	void Save()
	{
		if (!m_Data)
			m_Data = new ShopClaimActiveContainersFile();

		if (!m_Data.containers)
			m_Data.containers = new array<ref ShopClaimStoredContainer>();

		m_Data.version = 1;
		JsonFileLoader<ShopClaimActiveContainersFile>.JsonSaveFile(STORE_PATH, m_Data);
	}

	bool Has(string steamId)
	{
		return FindIndex(steamId) >= 0;
	}

	ShopClaimStoredContainer Get(string steamId)
	{
		int idx = FindIndex(steamId);
		if (idx < 0)
			return null;

		return m_Data.containers.Get(idx);
	}

	array<ref ShopClaimStoredContainer> GetAll()
	{
		if (!m_Data || !m_Data.containers)
			return new array<ref ShopClaimStoredContainer>();

		return m_Data.containers;
	}

	void Upsert(string steamId, string operationId, string containerClass, int pid1, int pid2, int pid3, int pid4)
	{
		if (!steamId || steamId == "" || !operationId || operationId == "")
			return;

		if (!m_Data)
			m_Data = new ShopClaimActiveContainersFile();

		if (!m_Data.containers)
			m_Data.containers = new array<ref ShopClaimStoredContainer>();

		ref ShopClaimStoredContainer entry = Get(steamId);
		if (!entry)
		{
			entry = new ShopClaimStoredContainer();
			m_Data.containers.Insert(entry);
		}

		entry.steam_id = steamId;
		entry.operation_id = operationId;

		if (containerClass && containerClass != "")
			entry.container_class = containerClass;

		if (pid1 != 0 || pid2 != 0 || pid3 != 0 || pid4 != 0)
		{
			entry.pid1 = pid1;
			entry.pid2 = pid2;
			entry.pid3 = pid3;
			entry.pid4 = pid4;
		}

		if (!entry.spawned_at || entry.spawned_at == "")
		{
			entry.spawned_at = ShopClaimTimeHelper.NowIso();
			entry.spawned_minutes = ShopClaimTimeHelper.NowMinutes();
		}

		Save();
	}

	void UpdatePersistentIds(string steamId, int pid1, int pid2, int pid3, int pid4)
	{
		ref ShopClaimStoredContainer entry = Get(steamId);
		if (!entry)
			return;

		if (pid1 == 0 && pid2 == 0 && pid3 == 0 && pid4 == 0)
			return;

		entry.pid1 = pid1;
		entry.pid2 = pid2;
		entry.pid3 = pid3;
		entry.pid4 = pid4;
		Save();
	}

	void Remove(string steamId)
	{
		int idx = FindIndex(steamId);
		if (idx < 0)
			return;

		m_Data.containers.Remove(idx);
		Save();
	}

	protected int FindIndex(string steamId)
	{
		if (!m_Data || !m_Data.containers || !steamId || steamId == "")
			return -1;

		for (int i = 0; i < m_Data.containers.Count(); i++)
		{
			ref ShopClaimStoredContainer entry = m_Data.containers.Get(i);
			if (entry && entry.steam_id == steamId)
				return i;
		}

		return -1;
	}
};

class ShopClaimTimeHelper
{
	static int NowMinutes()
	{
		int year, month, day, hour, minute;
		GetGame().GetWorld().GetDate(year, month, day, hour, minute);
		return year * 525600 + month * 43200 + day * 1440 + hour * 60 + minute;
	}

	static string NowIso()
	{
		int year, month, day, hour, minute;
		GetGame().GetWorld().GetDate(year, month, day, hour, minute);
		return year.ToString() + "-" + Pad2(month) + "-" + Pad2(day) + "T" + Pad2(hour) + ":" + Pad2(minute) + ":00Z";
	}

	protected static string Pad2(int value)
	{
		if (value < 10)
			return "0" + value.ToString();
		return value.ToString();
	}

	static int MinutesSince(int spawnedMinutes)
	{
		if (spawnedMinutes <= 0)
			return 0;

		return NowMinutes() - spawnedMinutes;
	}
};
