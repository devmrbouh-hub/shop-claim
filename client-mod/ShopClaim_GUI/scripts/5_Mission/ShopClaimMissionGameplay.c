modded class MissionGameplay
{
	override void OnInit()
	{
		super.OnInit();
		ShopClaimClientRpc.InitClient();
	}

	override void OnUpdate(float timeslice)
	{
		super.OnUpdate(timeslice);

		if (!GetGame() || !GetGame().GetUIManager())
			return;

		if (GetUApi().GetInputByName("UAShopClaimOpenShop").LocalPress())
			ShopClaimMenu.TryOpen();

		if (ShopClaimMenu.IsOpen() && GetUApi().GetInputByName("UAUIBack").LocalPress())
			ShopClaimMenu.CloseIfOpen();
	}
};
