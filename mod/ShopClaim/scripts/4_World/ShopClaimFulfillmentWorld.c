class ShopClaimFulfillmentWorld
{
	static void OnItemTaken(string operationId, EntityAI item)
	{
		if (!operationId || operationId == "" || !item)
			return;

		string className = item.GetType();
		ref array<string> itemAttachments = CollectAttachmentClassNames(item);
		int takeQty = GetLedgerUnitCount(ItemBase.Cast(item), className);

		if (!ShopClaimFulfillmentStore.Get().DecrementLine(operationId, className, itemAttachments, takeQty))
			ShopClaimLogger.Info("Fulfillment: unmatched take class=" + className + " op=" + operationId);
	}

	static void ReconcileFromCargo(string operationId, EntityAI container)
	{
		if (!operationId || operationId == "" || !container)
			return;

		array<ref ShopClaimFulfillmentLine> lines = ShopClaimFulfillmentStore.Get().GetLines(operationId);
		if (!lines)
			return;

		foreach (ShopClaimFulfillmentLine line : lines)
		{
			if (!line)
				continue;

			int inCargo = CountMatchingInCargo(container, line.class_name, line.attachments);
			int before = line.qty_remaining;

			if (inCargo < line.qty_remaining)
				line.qty_remaining = inCargo;

			if (before != line.qty_remaining)
			{
				ShopClaimLogger.Info("Fulfillment reconcile op=" + operationId + " class=" + line.class_name + " inCargo=" + inCargo.ToString() + " qty_remaining=" + before.ToString() + "->" + line.qty_remaining.ToString());
			}
		}

		ShopClaimFulfillmentStore.Get().Save();
	}

	protected static bool UseQuantityForLedger(string className)
	{
		if (!className || className == "")
			return false;

		return className.IndexOf("Money_Ruble") == 0;
	}

	protected static int GetLedgerUnitCount(ItemBase itemBase, string className)
	{
		if (!UseQuantityForLedger(className))
			return 1;

		if (!itemBase || !itemBase.HasQuantity())
			return 1;

		int q = itemBase.GetQuantity();
		if (q > 0)
			return q;

		return 1;
	}

	protected static int CountMatchingInCargo(EntityAI container, string className, array<string> expectedAttachments)
	{
		if (!container || !container.GetInventory())
			return 0;

		CargoBase cargo = container.GetInventory().GetCargo();
		if (!cargo)
			return 0;

		int count = 0;
		int itemCount = cargo.GetItemCount();

		for (int i = 0; i < itemCount; i++)
		{
			EntityAI entity = cargo.GetItem(i);
			if (!entity)
				continue;

			if (entity.GetType() != className)
				continue;

			ref array<string> itemAttachments = CollectAttachmentClassNames(entity);
			if (!AttachmentsMatch(expectedAttachments, itemAttachments))
				continue;

			count = count + GetLedgerUnitCount(ItemBase.Cast(entity), className);
		}

		return count;
	}

	protected static ref array<string> CollectAttachmentClassNames(EntityAI entity)
	{
		ref array<string> result = new array<string>();

		if (!entity || !entity.GetInventory())
			return result;

		int count = entity.GetInventory().AttachmentCount();
		for (int i = 0; i < count; i++)
		{
			EntityAI att = entity.GetInventory().GetAttachmentFromIndex(i);
			if (att)
				result.Insert(att.GetType());
		}

		return result;
	}

	protected static bool AttachmentsMatch(array<string> expected, array<string> actual)
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
