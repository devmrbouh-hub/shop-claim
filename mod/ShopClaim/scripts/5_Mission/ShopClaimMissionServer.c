modded class MissionServer
{
	override void OnInit()
	{
		super.OnInit();
		ShopClaimSettings.Load();
		ShopClaimContainerTracker.Get().LoadPendingFromStore();
		ShopClaimContainerTracker.Get().Start();
		ShopClaimGuiRpc.Get().InitServer();

		ref ShopClaimContainerTracker tracker = ShopClaimContainerTracker.Get();
		GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(tracker.RestoreTimeout, 600000, false);

		ShopClaimLogger.Info("MissionServer initialized");
	}
};
