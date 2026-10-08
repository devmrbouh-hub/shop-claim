class ShopClaimSpawnSurfaceParams
{
	float DistanceM;
	float MaxSlopeDeg;
	float CheckRadiusM;
	float HeightOffset;

	void ShopClaimSpawnSurfaceParams()
	{
		DistanceM = 1.2;
		MaxSlopeDeg = 25.0;
		CheckRadiusM = 0.8;
		HeightOffset = 0.05;
	}
};

class ShopClaimSpawnSurface
{
	static bool FindPositionNearPlayer(PlayerBase player, ShopClaimSpawnSurfaceParams params, out vector spawnPos)
	{
		spawnPos = "0 0 0";

		if (!player || !params)
			return false;

		float distance = params.DistanceM;
		if (distance <= 0)
			distance = 1.2;

		float maxSlope = params.MaxSlopeDeg;
		if (maxSlope <= 0)
			maxSlope = 25.0;

		float checkRadius = params.CheckRadiusM;
		if (checkRadius <= 0)
			checkRadius = 0.8;

		vector eyePos = player.GetPosition();
		eyePos[1] = eyePos[1] + 1.6;

		vector dir = player.GetDirection();
		float dirLen = dir.Length();
		if (dirLen > 0.001)
			dir = dir * (1.0 / dirLen);

		vector targetPos = eyePos + (dir * distance);
		float surfaceY = GetGame().SurfaceY(targetPos[0], targetPos[2]);
		spawnPos = targetPos;
		spawnPos[1] = surfaceY + params.HeightOffset;

		if (!IsRaycastClear(eyePos, spawnPos, player))
			return false;

		if (GetGame().SurfaceIsSea(spawnPos[0], spawnPos[2]))
			return false;

		if (!IsSlopeAllowed(spawnPos, maxSlope))
			return false;

		if (!IsAreaClear(spawnPos, checkRadius, player))
			return false;

		return true;
	}

	static bool IsRaycastClear(vector from, vector to, PlayerBase player)
	{
		vector contactPos;
		vector contactDir;
		int contactComponent;
		bool hit = DayZPhysics.RaycastRV(from, to, contactPos, contactDir, contactComponent, null, null, player, false, false, ObjIntersectGeom, 0.25);
		return !hit;
	}

	static bool IsSlopeAllowed(vector pos, float maxSlopeDeg)
	{
		vector normal = GetGame().SurfaceGetNormal(pos[0], pos[2]);
		if (normal[1] >= 0.999)
			return true;

		float slopeDeg = Math.Acos(normal[1]) * Math.RAD2DEG;
		return slopeDeg <= maxSlopeDeg;
	}

	static bool IsAreaClear(vector pos, float radius, PlayerBase player)
	{
		array<Object> objects = new array<Object>();
		GetGame().GetObjectsAtPosition(pos, radius, objects, null);

		foreach (Object obj : objects)
		{
			if (!obj)
				continue;

			if (obj == player)
				continue;

			EntityAI entity = EntityAI.Cast(obj);
			if (entity)
				return false;
		}

		return true;
	}
};
