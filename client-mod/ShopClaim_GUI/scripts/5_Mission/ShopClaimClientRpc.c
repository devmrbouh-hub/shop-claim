// RPC namespace/names must match server mod: mod/ShopClaim/scripts/3_Game/ShopClaimRpcNames.c
class ShopClaimClientRpc
{
	protected static const string RPC_MOD = "ShopClaim";

	protected static ref ShopClaimClientRpc s_Instance;

	static ShopClaimClientRpc Get()
	{
		if (!s_Instance)
			s_Instance = new ShopClaimClientRpc();
		return s_Instance;
	}

	static void InitClient()
	{
		Get().RegisterHandlers();
	}

	void RegisterHandlers()
	{
		GetRPCManager().AddRPC(RPC_MOD, "SyncPendingList", this, SingleplayerExecutionType.Client);
		GetRPCManager().AddRPC(RPC_MOD, "SyncPendingError", this, SingleplayerExecutionType.Client);
		GetRPCManager().AddRPC(RPC_MOD, "ClaimResult", this, SingleplayerExecutionType.Client);
	}

	void RequestPendingList()
	{
		GetRPCManager().SendRPC(RPC_MOD, "RequestPendingList", null, true);
	}

	void Claim(string operationId)
	{
		if (!operationId || operationId == "")
			return;

		GetRPCManager().SendRPC(RPC_MOD, "Claim", new Param1<string>(operationId), true);
	}

	void RespawnContainer()
	{
		GetRPCManager().SendRPC(RPC_MOD, "RespawnContainer", null, true);
	}

	void SyncPendingList(CallType type, ParamsReadContext ctx, PlayerIdentity sender, Object target)
	{
		if (type != CallType.Client)
			return;

		if (!ShopClaimMenu.IsOpen())
			return;

		Param1<string> data;
		if (!ctx.Read(data))
			return;

		array<ref ShopClaimGuiOrderRow> rows;
		string activeContainerOperationId;
		string themePrefix;
		ShopClaimGuiDto.ParsePendingEnvelope(data.param1, rows, activeContainerOperationId, themePrefix);
		ShopClaimMenu.GetInstance().OnSyncPendingList(rows, activeContainerOperationId, themePrefix);
	}

	void SyncPendingError(CallType type, ParamsReadContext ctx, PlayerIdentity sender, Object target)
	{
		if (type != CallType.Client)
			return;

		if (!ShopClaimMenu.IsOpen())
			return;

		Param1<string> data;
		if (!ctx.Read(data))
			return;

		string message;
		string themePrefix;
		ShopClaimGuiDto.ParseSyncPendingError(data.param1, message, themePrefix);
		ShopClaimMenu.GetInstance().OnSyncPendingError(message, themePrefix);
	}

	void ClaimResult(CallType type, ParamsReadContext ctx, PlayerIdentity sender, Object target)
	{
		if (type != CallType.Client)
			return;

		if (!ShopClaimMenu.IsOpen())
			return;

		Param3<bool, string, bool> data;
		if (!ctx.Read(data))
			return;

		ShopClaimMenu.GetInstance().OnClaimResult(data.param1, data.param2, data.param3);
	}
};
