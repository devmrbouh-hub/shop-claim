class ShopClaimItem
{
	string ClassName;
	int Qty;
	ref array<string> Attachments;

	void ShopClaimItem()
	{
		Qty = 1;
		Attachments = new array<string>();
	}
};

class ShopClaimPayload
{
	string Container;
	ref array<ref ShopClaimItem> Items;

	void ShopClaimPayload()
	{
		Items = new array<ref ShopClaimItem>();
	}
};

class ShopClaimVehicleSpawnConfig
{
	float DistanceM;
	float MaxSlopeDeg;
	float CheckRadiusM;

	void ShopClaimVehicleSpawnConfig()
	{
		DistanceM = 6.0;
		MaxSlopeDeg = 15.0;
		CheckRadiusM = 2.5;
	}
};

class ShopClaimVehicleDelivery
{
	string ClassName;
	ref array<string> SpawnAttachments;
	ref array<ref ShopClaimItem> CargoItems;
	float Fuel;
	float Coolant;
	ref ShopClaimVehicleSpawnConfig Spawn;

	void ShopClaimVehicleDelivery()
	{
		SpawnAttachments = new array<string>();
		CargoItems = new array<ref ShopClaimItem>();
		Fuel = -1;
		Coolant = -1;
		Spawn = new ShopClaimVehicleSpawnConfig();
	}
};

class ShopClaimPendingOrder
{
	string operation_id;
	string offer_id;
	string name;
	string type;
	string status;
	ref ShopClaimPayload delivery;
	ref ShopClaimVehicleDelivery vehicle;

	void ShopClaimPendingOrder()
	{
		delivery = new ShopClaimPayload();
		vehicle = new ShopClaimVehicleDelivery();
	}

	bool IsAvailable()
	{
		return status == "available";
	}

	bool IsSpawned()
	{
		return status == "spawned";
	}

	bool IsContainer()
	{
		return type == "container";
	}

	bool IsVehicle()
	{
		return type == "vehicle";
	}
};

class ShopClaimJsonHelper
{
	static int IndexOfFrom(string haystack, int from, string needle)
	{
		if (from >= haystack.Length())
			return -1;

		string tail = haystack.Substring(from, haystack.Length() - from);
		int idx = tail.IndexOf(needle);
		if (idx < 0)
			return -1;

		return from + idx;
	}

	static string TrimString(string value)
	{
		int start = 0;
		int end = value.Length();

		while (start < end)
		{
			string ch = value.Substring(start, 1);
			if (ch == " " || ch == "\t" || ch == "\n" || ch == "\r")
				start++;
			else
				break;
		}

		while (end > start)
		{
			string ch2 = value.Substring(end - 1, 1);
			if (ch2 == " " || ch2 == "\t" || ch2 == "\n" || ch2 == "\r")
				end--;
			else
				break;
		}

		if (end <= start)
			return "";

		return value.Substring(start, end - start);
	}

	static string GetStringField(string json, string fieldName)
	{
		string needle = "\"" + fieldName + "\":\"";
		int start = json.IndexOf(needle);
		if (start < 0)
			return "";

		start = start + needle.Length();
		int end = IndexOfFrom(json, start, "\"");
		if (end < 0)
			return "";

		return json.Substring(start, end - start);
	}

	static int GetIntField(string json, string fieldName)
	{
		string needle = "\"" + fieldName + "\":";
		int start = json.IndexOf(needle);
		if (start < 0)
			return 0;

		start = start + needle.Length();
		string tail = json.Substring(start, json.Length() - start);
		tail = TrimString(tail);

		int end = 0;
		while (end < tail.Length())
		{
			string ch = tail.Substring(end, 1);
			if (ch == "," || ch == "}" || ch == "]")
				break;
			end++;
		}

		string num = tail.Substring(0, end);
		return num.ToInt();
	}

	static void ParseDeliveryItems(string deliveryJson, out array<ref ShopClaimItem> items)
	{
		ParseDeliveryItemsField(deliveryJson, "items", items);
	}

	static void ParseDeliveryItemsField(string deliveryJson, string fieldName, out array<ref ShopClaimItem> items)
	{
		items = new array<ref ShopClaimItem>();

		int itemsPos = deliveryJson.IndexOf("\"" + fieldName + "\"");
		if (itemsPos < 0)
			return;

		int arrayStart = IndexOfFrom(deliveryJson, itemsPos, "[");
		if (arrayStart < 0)
			return;

		int depth = 0;
		int objectStart = -1;
		for (int i = arrayStart; i < deliveryJson.Length(); i++)
		{
			string ch = deliveryJson.Substring(i, 1);
			if (ch == "{")
			{
				if (depth == 0)
					objectStart = i;
				depth++;
			}
			else if (ch == "}")
			{
				depth--;
				if (depth == 0 && objectStart >= 0)
				{
					string itemJson = deliveryJson.Substring(objectStart, i - objectStart + 1);
					ref ShopClaimItem item = new ShopClaimItem();
					item.ClassName = GetStringField(itemJson, "class");
					item.Qty = GetIntField(itemJson, "qty");
					if (item.Qty < 1)
						item.Qty = 1;

					ParseAttachments(itemJson, item.Attachments);
					items.Insert(item);
					objectStart = -1;
				}
			}
			else if (ch == "]" && depth == 0)
			{
				break;
			}
		}
	}

	protected static void ParseStringArrayField(string json, string fieldName, out array<string> values)
	{
		values = new array<string>();

		string needle = "\"" + fieldName + "\"";
		int fieldPos = json.IndexOf(needle);
		if (fieldPos < 0)
			return;

		int arrayStart = IndexOfFrom(json, fieldPos, "[");
		if (arrayStart < 0)
			return;

		int arrayEnd = IndexOfFrom(json, arrayStart, "]");
		if (arrayEnd < 0)
			return;

		string inner = json.Substring(arrayStart + 1, arrayEnd - arrayStart - 1);
		array<string> parts = new array<string>();
		inner.Split(",", parts);

		foreach (string part : parts)
		{
			part = TrimString(part);
			part.Replace("\"", "");
			if (part != "")
				values.Insert(part);
		}
	}

	protected static bool GetBoolField(string json, string fieldName)
	{
		string needle = "\"" + fieldName + "\":true";
		return json.IndexOf(needle) >= 0;
	}

	protected static float GetFloatField(string json, string fieldName)
	{
		string needle = "\"" + fieldName + "\":";
		int start = json.IndexOf(needle);
		if (start < 0)
			return -1;

		start = start + needle.Length();
		string tail = json.Substring(start, json.Length() - start);
		tail = TrimString(tail);

		int end = 0;
		while (end < tail.Length())
		{
			string ch = tail.Substring(end, 1);
			if (ch == "," || ch == "}" || ch == "]")
				break;
			end++;
		}

		string num = tail.Substring(0, end);
		return num.ToFloat();
	}

	protected static void ParseVehicleSpawnConfig(string spawnJson, ShopClaimVehicleSpawnConfig spawn)
	{
		if (!spawn || !spawnJson || spawnJson == "")
			return;

		float distance = GetFloatField(spawnJson, "distance_m");
		if (distance > 0)
			spawn.DistanceM = distance;

		float slope = GetFloatField(spawnJson, "max_slope_deg");
		if (slope > 0)
			spawn.MaxSlopeDeg = slope;

		float radius = GetFloatField(spawnJson, "check_radius_m");
		if (radius > 0)
			spawn.CheckRadiusM = radius;
	}

	protected static void ParseVehicleDelivery(string deliveryJson, ShopClaimVehicleDelivery vehicle)
	{
		if (!vehicle || !deliveryJson || deliveryJson == "")
			return;

		vehicle.ClassName = GetStringField(deliveryJson, "class");
		ParseStringArrayField(deliveryJson, "spawn_attachments", vehicle.SpawnAttachments);
		ParseDeliveryItemsField(deliveryJson, "cargo_items", vehicle.CargoItems);

		int fluidsPos = deliveryJson.IndexOf("\"fluids\"");
		if (fluidsPos >= 0)
		{
			int fluidsStart = IndexOfFrom(deliveryJson, fluidsPos, "{");
			if (fluidsStart >= 0)
			{
				string fluidsJson = ExtractObject(deliveryJson, fluidsStart);
				vehicle.Fuel = GetFloatField(fluidsJson, "fuel");
				vehicle.Coolant = GetFloatField(fluidsJson, "coolant");
			}
		}

		int spawnPos = deliveryJson.IndexOf("\"spawn\"");
		if (spawnPos >= 0)
		{
			int spawnStart = IndexOfFrom(deliveryJson, spawnPos, "{");
			if (spawnStart >= 0)
			{
				string spawnJson = ExtractObject(deliveryJson, spawnStart);
				ParseVehicleSpawnConfig(spawnJson, vehicle.Spawn);
			}
		}
	}

	protected static void ParseAttachments(string itemJson, out array<string> attachments)
	{
		attachments = new array<string>();

		int attPos = itemJson.IndexOf("\"attachments\"");
		if (attPos < 0)
			return;

		int arrayStart = IndexOfFrom(itemJson, attPos, "[");
		if (arrayStart < 0)
			return;

		int arrayEnd = IndexOfFrom(itemJson, arrayStart, "]");
		if (arrayEnd < 0)
			return;

		string inner = itemJson.Substring(arrayStart + 1, arrayEnd - arrayStart - 1);
		array<string> parts = new array<string>();
		inner.Split(",", parts);

		foreach (string part : parts)
		{
			part = TrimString(part);
			part.Replace("\"", "");
			if (part != "")
				attachments.Insert(part);
		}
	}

	static bool ParsePendingOrders(string json, out array<ref ShopClaimPendingOrder> orders)
	{
		orders = new array<ref ShopClaimPendingOrder>();
		if (!json || json == "" || json == "[]")
			return true;

		int depth = 0;
		int objectStart = -1;
		for (int i = 0; i < json.Length(); i++)
		{
			string ch = json.Substring(i, 1);
			if (ch == "{")
			{
				if (depth == 0)
					objectStart = i;
				depth++;
			}
			else if (ch == "}")
			{
				depth--;
				if (depth == 0 && objectStart >= 0)
				{
					string orderJson = json.Substring(objectStart, i - objectStart + 1);
					ref ShopClaimPendingOrder order = new ShopClaimPendingOrder();
					order.operation_id = GetStringField(orderJson, "operation_id");
					order.offer_id = GetStringField(orderJson, "offer_id");
					order.name = GetStringField(orderJson, "name");
					order.type = GetStringField(orderJson, "type");
					order.status = GetStringField(orderJson, "status");
					order.delivery.Container = GetStringField(orderJson, "container");

					int deliveryPos = orderJson.IndexOf("\"delivery\"");
					if (deliveryPos >= 0)
					{
						int deliveryStart = IndexOfFrom(orderJson, deliveryPos, "{");
						if (deliveryStart >= 0)
						{
							string deliveryJson = ExtractObject(orderJson, deliveryStart);
							if (deliveryJson != "")
							{
								if (order.type == "vehicle")
								{
									ParseVehicleDelivery(deliveryJson, order.vehicle);
								}
								else
								{
									string container = GetStringField(deliveryJson, "container");
									if (container != "")
										order.delivery.Container = container;
									ParseDeliveryItems(deliveryJson, order.delivery.Items);
								}
							}
						}
					}

					orders.Insert(order);
					objectStart = -1;
				}
			}
		}

		return true;
	}

	protected static string ExtractObject(string json, int start)
	{
		int depth = 0;
		for (int i = start; i < json.Length(); i++)
		{
			string ch = json.Substring(i, 1);
			if (ch == "{")
				depth++;
			else if (ch == "}")
			{
				depth--;
				if (depth == 0)
					return json.Substring(start, i - start + 1);
			}
		}
		return "";
	}
};
