modded class Container_Base
{
	protected string m_ShopClaimSteamId;
	protected string m_ShopClaimOperationId;
	protected bool m_ShopClaimFilling;

	void Container_Base()
	{
		m_ShopClaimSteamId = "";
		m_ShopClaimOperationId = "";
		m_ShopClaimFilling = false;
	}

	bool IsShopClaimContainer()
	{
		return m_ShopClaimOperationId != "";
	}

	void ShopClaimMark(string steamId, string operationId)
	{
		m_ShopClaimSteamId = steamId;
		m_ShopClaimOperationId = operationId;
		SetSynchDirty();
	}

	void ShopClaimBeginFill()
	{
		m_ShopClaimFilling = true;
	}

	void ShopClaimEndFill()
	{
		m_ShopClaimFilling = false;
	}

	string ShopClaimGetOperationId()
	{
		return m_ShopClaimOperationId;
	}

	override void EEItemDetached(EntityAI item, string slot_name)
	{
		super.EEItemDetached(item, slot_name);

		if (!GetGame().IsServer())
			return;

		if (!IsShopClaimContainer() || m_ShopClaimFilling)
			return;

		if (!item)
			return;

		ShopClaimFulfillmentWorld.OnItemTaken(m_ShopClaimOperationId, item);
	}

	override bool IsTakeable()
	{
		if (IsShopClaimContainer())
			return false;

		return super.IsTakeable();
	}

	override bool CanPutIntoHands(EntityAI parent)
	{
		if (IsShopClaimContainer())
			return false;

		return super.CanPutIntoHands(parent);
	}

	override bool CanReceiveItemIntoCargo(EntityAI item)
	{
		if (IsShopClaimContainer() && !m_ShopClaimFilling)
			return false;

		return super.CanReceiveItemIntoCargo(item);
	}

	override bool CanReceiveAttachment(EntityAI attachment, int slotId)
	{
		if (IsShopClaimContainer() && !m_ShopClaimFilling)
			return false;

		return super.CanReceiveAttachment(attachment, slotId);
	}

	override bool CanSwapItemInCargo(EntityAI child_entity, EntityAI new_entity)
	{
		if (IsShopClaimContainer() && !m_ShopClaimFilling)
			return false;

		return super.CanSwapItemInCargo(child_entity, new_entity);
	}

	override void OnStoreSave(ParamsWriteContext ctx)
	{
		super.OnStoreSave(ctx);
		ctx.Write(m_ShopClaimSteamId);
		ctx.Write(m_ShopClaimOperationId);
	}

	override bool OnStoreLoad(ParamsReadContext ctx, int version)
	{
		if (!super.OnStoreLoad(ctx, version))
			return false;

		if (!ctx.Read(m_ShopClaimSteamId))
			m_ShopClaimSteamId = "";

		if (!ctx.Read(m_ShopClaimOperationId))
			m_ShopClaimOperationId = "";

		return true;
	}

	override void AfterStoreLoad()
	{
		super.AfterStoreLoad();

		if (!GetGame().IsServer())
			return;

		if (!IsShopClaimContainer())
			return;

		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(ShopClaimTryRegisterSelf, 500, false);
	}

	protected void ShopClaimTryRegisterSelf()
	{
		if (!IsAlive() || !IsShopClaimContainer())
			return;

		ShopClaimContainerTracker.Get().RegisterSelf(m_ShopClaimSteamId, m_ShopClaimOperationId, this);
	}
};
