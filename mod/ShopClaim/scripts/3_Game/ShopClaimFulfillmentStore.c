class ShopClaimFulfillmentLine
{
	string class_name;
	int qty_total;
	int qty_remaining;
	ref array<string> attachments;

	void ShopClaimFulfillmentLine()
	{
		qty_total = 0;
		qty_remaining = 0;
		attachments = new array<string>();
	}
};

class ShopClaimFulfillmentOperation
{
	string operation_id;
	ref array<ref ShopClaimFulfillmentLine> items;

	void ShopClaimFulfillmentOperation()
	{
		operation_id = "";
		items = new array<ref ShopClaimFulfillmentLine>();
	}
};

class ShopClaimFulfillmentFile
{
	int version;
	ref array<ref ShopClaimFulfillmentOperation> operations;

	void ShopClaimFulfillmentFile()
	{
		version = 1;
		operations = new array<ref ShopClaimFulfillmentOperation>();
	}
};

class ShopClaimFulfillmentStore
{
	protected static ref ShopClaimFulfillmentStore s_Instance;
	protected static const string STORE_PATH = "$profile:ShopClaim/fulfillment.json";
	protected ref ShopClaimFulfillmentFile m_Data;

	void ShopClaimFulfillmentStore()
	{
		m_Data = new ShopClaimFulfillmentFile();
		Load();
	}

	static ShopClaimFulfillmentStore Get()
	{
		if (!s_Instance)
			s_Instance = new ShopClaimFulfillmentStore();
		return s_Instance;
	}

	void Load()
	{
		m_Data = new ShopClaimFulfillmentFile();

		if (!FileExist(STORE_PATH))
			return;

		JsonFileLoader<ShopClaimFulfillmentFile>.JsonLoadFile(STORE_PATH, m_Data);

		if (!m_Data)
			m_Data = new ShopClaimFulfillmentFile();

		if (!m_Data.operations)
			m_Data.operations = new array<ref ShopClaimFulfillmentOperation>();

		if (m_Data.version < 1)
			m_Data.version = 1;
	}

	void Save()
	{
		if (!m_Data)
			m_Data = new ShopClaimFulfillmentFile();

		if (!m_Data.operations)
			m_Data.operations = new array<ref ShopClaimFulfillmentOperation>();

		m_Data.version = 1;
		JsonFileLoader<ShopClaimFulfillmentFile>.JsonSaveFile(STORE_PATH, m_Data);
	}

	bool HasOperation(string operationId)
	{
		return GetOperation(operationId) != null;
	}

	ShopClaimFulfillmentOperation GetOperation(string operationId)
	{
		if (!operationId || operationId == "" || !m_Data || !m_Data.operations)
			return null;

		foreach (ShopClaimFulfillmentOperation op : m_Data.operations)
		{
			if (op && op.operation_id == operationId)
				return op;
		}

		return null;
	}

	bool HasRemaining(string operationId)
	{
		ShopClaimFulfillmentOperation op = GetOperation(operationId);
		if (!op || !op.items)
			return false;

		foreach (ShopClaimFulfillmentLine line : op.items)
		{
			if (line && line.qty_remaining > 0)
				return true;
		}

		return false;
	}

	void InitFromOrder(string operationId, array<ref ShopClaimItem> catalogItems)
	{
		if (!operationId || operationId == "" || !catalogItems)
			return;

		ref ShopClaimFulfillmentOperation op = GetOperation(operationId);
		if (!op)
		{
			op = new ShopClaimFulfillmentOperation();
			op.operation_id = operationId;
			m_Data.operations.Insert(op);
		}

		op.items = new array<ref ShopClaimFulfillmentLine>();

		foreach (ShopClaimItem item : catalogItems)
		{
			if (!item || item.ClassName == "")
				continue;

			ref ShopClaimFulfillmentLine line = new ShopClaimFulfillmentLine();
			line.class_name = item.ClassName;
			line.qty_total = item.Qty;
			if (line.qty_total < 1)
				line.qty_total = 1;
			line.qty_remaining = line.qty_total;

			if (item.Attachments)
			{
				foreach (string att : item.Attachments)
				{
					if (att && att != "")
						line.attachments.Insert(att);
				}
			}

			op.items.Insert(line);
		}

		Save();
	}

	void RemoveOperation(string operationId)
	{
		if (!operationId || operationId == "" || !m_Data || !m_Data.operations)
			return;

		for (int i = m_Data.operations.Count() - 1; i >= 0; i--)
		{
			ShopClaimFulfillmentOperation op = m_Data.operations.Get(i);
			if (op && op.operation_id == operationId)
			{
				m_Data.operations.Remove(i);
				Save();
				return;
			}
		}
	}

	bool DecrementLine(string operationId, string className, array<string> itemAttachments, int takeQty)
	{
		if (!operationId || operationId == "" || !className || className == "" || takeQty < 1)
			return false;

		ShopClaimFulfillmentOperation op = GetOperation(operationId);
		if (!op || !op.items)
			return false;

		foreach (ShopClaimFulfillmentLine line : op.items)
		{
			if (!line || line.qty_remaining <= 0)
				continue;

			if (line.class_name != className)
				continue;

			if (!AttachmentsMatch(line.attachments, itemAttachments))
				continue;

			int dec = takeQty;
			if (dec > line.qty_remaining)
				dec = line.qty_remaining;

			line.qty_remaining = line.qty_remaining - dec;
			Save();
			return true;
		}

		return false;
	}

	void SetLineRemaining(string operationId, string className, array<string> expectedAttachments, int remaining)
	{
		ShopClaimFulfillmentOperation op = GetOperation(operationId);
		if (!op || !op.items)
			return;

		foreach (ShopClaimFulfillmentLine line : op.items)
		{
			if (!line || line.class_name != className)
				continue;

			if (!AttachmentsMatch(line.attachments, expectedAttachments))
				continue;

			if (remaining < 0)
				remaining = 0;

			line.qty_remaining = remaining;
			return;
		}
	}

	int GetLineRemaining(string operationId, string className, array<string> expectedAttachments)
	{
		ShopClaimFulfillmentOperation op = GetOperation(operationId);
		if (!op || !op.items)
			return 0;

		foreach (ShopClaimFulfillmentLine line : op.items)
		{
			if (!line || line.class_name != className)
				continue;

			if (!AttachmentsMatch(line.attachments, expectedAttachments))
				continue;

			return line.qty_remaining;
		}

		return 0;
	}

	array<ref ShopClaimFulfillmentLine> GetLines(string operationId)
	{
		ShopClaimFulfillmentOperation op = GetOperation(operationId);
		if (!op)
			return null;

		return op.items;
	}

	protected bool AttachmentsMatch(array<string> expected, array<string> actual)
	{
		int expectedCount = 0;
		if (expected)
			expectedCount = expected.Count();

		int actualCount = 0;
		if (actual)
			actualCount = actual.Count();

		if (expectedCount == 0 && actualCount == 0)
			return true;

		if (expectedCount != actualCount)
			return false;

		foreach (string exp : expected)
		{
			bool found = false;
			foreach (string act : actual)
			{
				if (exp == act)
				{
					found = true;
					break;
				}
			}

			if (!found)
				return false;
		}

		return true;
	}
};
