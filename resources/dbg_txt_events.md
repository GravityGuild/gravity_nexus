# dgb.txt log events

## Timezone

Logged when starting a fresh client

``` text
2026-05-27 07:36:42	Timezone: UTC-6h00m
```


## /q

Quit out of game to login screen

``` text
2026-05-27 07:24:31	*** DISCONNECTING: Quit command received.
2026-05-27 07:24:31	*** WARNING: ProcessGame.  Dropped out of game loop.
```


## /exit

Exit out of the completely

``` text
2026-05-27 07:30:39	*** DISCONNECTING: Exit command received.
2026-05-27 07:30:39	
```


## /camp

Camp/log out to character select

``` text
2026-05-27 07:38:04	*** EXITING: I have completed camping.
2026-05-27 07:38:04	
2026-05-27 07:38:04	Networking: connection terminated [client:DisconnectReasonOtherSideTerminated,server:DisconnectReasonNone]
2026-05-27 07:38:04	Networking: Connection Closed [0] with 0 pending bytes.
2026-05-27 07:38:04	Attempt to send message 29547 on a void connection.
2026-05-27 07:38:04	Cleaning up groups.
2026-05-27 07:38:04	Attempt to send message 3702 on a void connection.
2026-05-27 07:38:04	Stopping world display.
2026-05-27 07:38:04	Attempt to send message 30546 on a void connection.
2026-05-27 07:38:04	Cleaning up.
2026-05-27 07:38:04	Sending Logout.
2026-05-27 07:38:04	Attempt to send message 3942 on a void connection.
2026-05-27 07:38:04	Networking: using port [49764].
2026-05-27 07:38:04	Networking: Connection Established [1]
2026-05-27 07:38:04	WorldAuthenticate: Initiating Login.
2026-05-27 07:38:04	WorldAuthenticate.  I got a message of type 0x3c25 (15397).
2026-05-27 07:38:07	WorldAuthenticate.  I got a message of type 0x6957 (26967).
2026-05-27 07:38:07	WorldAuthenticate.  I got a message of type 0x4513 (17683).
2026-05-27 07:38:07	Check 1sa. 0xce8a68fb
2026-05-27 07:38:07	
2026-05-27 07:38:07	Check 1x. 0x9e15bc94
2026-05-27 07:38:07	
2026-05-27 07:38:07	WorldAuthenticate.  I got a message of type 0x7cba (31930).
2026-05-27 07:38:07	WorldAuthenticate.  I got a message of type 0x52a4 (21156).
2026-05-27 07:38:07	WorldAuthenticate.  Access granted.
2026-05-27 07:38:07	
2026-05-27 07:38:07	Starting network game.
2026-05-27 07:38:07	
2026-05-27 07:38:07	Starting load.
2026-05-27 07:38:07	
2026-05-27 07:38:07	Attempting to load load.EQG.
2026-05-27 07:38:07	Verifying world files.
2026-05-27 07:38:07	Loading zone specific files.
2026-05-27 07:38:07	Loading load_obj2
2026-05-27 07:38:07	Loading load_obj
2026-05-27 07:38:08	Loading load_chr2
2026-05-27 07:38:08	Loading load_chr
2026-05-27 07:38:08	Loading load
2026-05-27 07:38:08	Loading objects
2026-05-27 07:38:08	Loading lights
2026-05-27 07:38:08	Initializing cameras.
2026-05-27 07:38:08	Initializing lights.
2026-05-27 07:38:08	Initializing visual effects.
2026-05-27 07:38:08	Initializing target indicator.
2026-05-27 07:38:08	Initializing player path.
2026-05-27 07:38:08	Performing post-load operations.
2026-05-27 07:38:08	Initializing precipitation system.
2026-05-27 07:38:08	World initialized: load
2026-05-27 07:38:08	load done.
2026-05-27 07:38:08	
2026-05-27 07:38:08	Starting char select.
2026-05-27 07:38:08	
2026-05-27 07:38:08	Clearing display buffers.
2026-05-27 07:38:08	
2026-05-27 07:38:08	Display buffers cleared.
2026-05-27 07:38:08	
2026-05-27 07:38:08	Initializing character select UI.
2026-05-27 07:38:08	Resetting game UI.
```


## /camp desktop

Camp/log out to desktop

``` text
2026-05-27 07:33:23	
2026-05-27 07:34:40	*** EXITING: I have completed camping.
2026-05-27 07:34:40	
2026-05-27 07:34:40	Networking: connection terminated [client:DisconnectReasonOtherSideTerminated,server:DisconnectReasonNone]
2026-05-27 07:34:40	Networking: Connection Closed [0] with 0 pending bytes.
2026-05-27 07:34:40	Attempt to send message 29547 on a void connection.
2026-05-27 07:34:40	Cleaning up groups.
2026-05-27 07:34:40	Attempt to send message 3702 on a void connection.
2026-05-27 07:34:40	Stopping world display.
2026-05-27 07:34:41	Attempt to send message 30546 on a void connection.
2026-05-27 07:34:41	Exiting normally.
2026-05-27 07:34:41	Cleanup 1
2026-05-27 07:34:41	
2026-05-27 07:34:41	Cleanup 4
2026-05-27 07:34:41	
2026-05-27 07:34:41	Cleanup 5
2026-05-27 07:34:41	
2026-05-27 07:34:41	Cleanup 6
2026-05-27 07:34:41	
2026-05-27 07:34:41	Cleanup 7
2026-05-27 07:34:41	
2026-05-27 07:34:41	Cleanup 8
2026-05-27 07:34:41	
2026-05-27 07:34:41	Cleanup 9
2026-05-27 07:34:41	
2026-05-27 07:34:41	Cleanup 10
2026-05-27 07:34:41	
2026-05-27 07:34:41	Resetting UI.
2026-05-27 07:34:41	Resetting character select UI.
2026-05-27 07:34:41	Resetting game UI.
2026-05-27 07:34:41	UI Reset.
2026-05-27 07:34:41	Cleanup 11
2026-05-27 07:34:41	
2026-05-27 07:34:41	SETD
```


## Logging back in

Character is logged in and selects a server to load to character select

``` text
2026-05-27 09:07:24	Server selected 70.35.159.51 (4737943).
2026-05-27 09:07:24	Initializing DirectInput.
2026-05-27 09:07:24	Initializing Keyboard.
2026-05-27 09:07:24	Initializing Mouse.
2026-05-27 09:07:24	Creating font list.
2026-05-27 09:07:24	Creating game object.
2026-05-27 09:07:24	Deleting obsolete files.
2026-05-27 09:07:24	Loading string tables.
2026-05-27 09:07:24	Initializing client variables.
2026-05-27 09:07:24	Loading spell effects.
2026-05-27 09:07:24	Initializing display structures.
2026-05-27 09:07:24	Sound Manager loaded 2165 filenames from soundassets.txt.
2026-05-27 09:07:25	Voice Manager loaded 12 macros from VoiceData.txt.
2026-05-27 09:07:25	Networking: using port [59251].
2026-05-27 09:07:25	Networking: Connection Established [1]
2026-05-27 09:07:25	WorldAuthenticate: Initiating Login.
2026-05-27 09:07:25	WorldAuthenticate.  I got a message of type 0xfa6 (4006).
2026-05-27 09:07:25	WorldRPServer message: server name project1999
2026-05-27 09:07:25	
2026-05-27 09:07:25	WorldAuthenticate.  I got a message of type 0x4ec (1260).
2026-05-27 09:07:25	WorldAuthenticate.  I got a message of type 0x3c25 (15397).
2026-05-27 09:07:28	WorldAuthenticate.  I got a message of type 0x6957 (26967).
2026-05-27 09:07:28	WorldAuthenticate.  I got a message of type 0x4513 (17683).
2026-05-27 09:07:28	Check 1sa. 0xce8a68fb
2026-05-27 09:07:28	
2026-05-27 09:07:28	Check 1x. 0x9e15bc94
2026-05-27 09:07:28	
2026-05-27 09:07:28	WorldAuthenticate.  I got a message of type 0x7cba (31930).
2026-05-27 09:07:28	WorldAuthenticate.  I got a message of type 0x52a4 (21156).
2026-05-27 09:07:28	WorldAuthenticate.  Access granted.
2026-05-27 09:07:28	
2026-05-27 09:07:28	Player Animations loaded 9 specific sounds from file AnimationSounds.txt.
2026-05-27 09:07:28	Initializing display.
2026-05-27 09:07:28	Initializing Particle System.
2026-05-27 09:07:28	Setting display options.
2026-05-27 09:07:28	CRender::InitDevice: Using 32bit mode.
2026-05-27 09:07:28	CRender::InitDevice: Using vsync 0.
2026-05-27 09:07:28	CRender::InitDevice: Using 24bit depth buffer with 8 bit stencil.
2026-05-27 09:07:28	CRender::InitDevice: HardwareTnL Enabled.  
2026-05-27 09:07:28	Using hardware vertex shaders. 
2026-05-27 09:07:28	Initializing render system.
2026-05-27 09:07:28	Trilinear Mipmapping available.
2026-05-27 09:07:28	Vertex Shader Version: 3.0 
2026-05-27 09:07:28	Pixel Shader Version: 3.0 
2026-05-27 09:07:28	RenderEffects\SPL/Lit.fxo is using Technique: Lit_DX6_FF_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/RegionOldDetailSingle.fxo is using Technique: DetailSingle_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/RegionOldDetailPalette.fxo is using Technique: DetailPalette_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/RegionC1.fxo is using Technique: RegionC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/RegionCG1.fxo is using Technique: RegionCG1_DX6_VS1_PS0_1Pass 
2026-05-27 09:07:28	RenderEffects\SPL/RegionCE1.fxo is using Technique: RegionCE1_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/RegionCB1.fxo is using Technique: RegionCB1_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/RegionCBS1.fxo is using Technique: RegionCBS1_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/RegionCBSG1.fxo is using Technique: RegionCBSG1_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/RegionCBSGE1.fxo is using Technique: RegionCBSGE1_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/RegionC1_2UV.fxo is using Technique: RegionC1_2UV_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/RegionCB1_2UV.fxo is using Technique: RegionCB1_2UV_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/RegionCBSG1_2UV.fxo is using Technique: RegionCBSG1_2UV_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/RegionTerrain.fxo is using Technique: RegionTerrain_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/RegionLava.fxo is using Technique: RegionLava_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/RegionLava2.fxo is using Technique: RegionLava2_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SModelC1.fxo is using Technique: SModelC1Prelit_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/SModelCG1.fxo is using Technique: SModelCG1Prelit_DX6_VS1_PS0_1Pass 
2026-05-27 09:07:28	RenderEffects\SPL/SModelCE1.fxo is using Technique: SModelCE1Prelit_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SModelCB1.fxo is using Technique: SModelCB1Prelit_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/SModelCBS1.fxo is using Technique: SModelCBS1Prelit_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SModelCBSG1.fxo is using Technique: SModelCBSG1Prelit_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SModelCBSGE1.fxo is using Technique: SModelCBSGE1Prelit_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SModelC1_2UV.fxo is using Technique: SModelC1_2UVPrelit_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/SModelCB1_2UV.fxo is using Technique: SModelCB1_2UVPrelit_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/SModelCBSG1_2UV.fxo is using Technique: SModelCBSG1_2UVPrelit_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SModelLava.fxo is using Technique: SModelLavaPrelit_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/SModelLava2.fxo is using Technique: SModelLava2Prelit_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshC1.fxo is using Technique: SkinMeshC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshCG1.fxo is using Technique: SkinMeshCG1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshCE1.fxo is using Technique: SkinMeshCE1_DX9_VS2_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshCB1.fxo is using Technique: SkinMeshCB1_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshCBS1.fxo is using Technique: SkinMeshCBS1_DX9_VS2_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshCBSG1.fxo is using Technique: SkinMeshCBSG1_DX9_VS2_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshCBSGE1.fxo is using Technique: SkinMeshCBSGE1_DX9_VS2_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshLava.fxo is using Technique: SkinMeshLava_DX9_VS2_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshLava2.fxo is using Technique: SkinMeshLava2_DX9_VS2_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshOld.fxo is using Technique: SkinMeshOld_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshLuclin.fxo is using Technique: SkinMeshLuclin_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshLuclinT1.fxo is using Technique: SkinMeshLuclinT1_DX6_VS1_PS0_1Pass 
2026-05-27 09:07:28	RenderEffects\SPL/RegionOldA.fxo is using Technique: RegionOldA_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/RegionWater.fxo is using Technique: RegionWater_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/RegionWaterFall.fxo is using Technique: RegionWaterFall_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/RegionLavaH.fxo is using Technique: RegionLava_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SModelWater.fxo is using Technique: SModelWater_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SkinMeshWater.fxo is using Technique: SkinMeshCBSGE1_DX9_VS2_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/Region_Basic.fxo is using Technique: RegionBasic_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/Region_Blend.fxo is using Technique: RegionBlnd_DX8_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/Region_BlendNoBump.fxo is using Technique: RegionBlndNoBump_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/Region_Full.fxo is using Technique: RegionFull_DX8_VS1_PS14_Norm_Pow 
2026-05-27 09:07:28	RenderEffects\SPL/Region_Full_2UV.fxo is using Technique: RegionFull2UV_DX8_VS1_PS14_Norm_Pow 
2026-05-27 09:07:28	RenderEffects\SPL/Region_Bump.fxo is using Technique: RegionBump_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/Region_Bump_2UV.fxo is using Technique: RegionBump2UV_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/Region_SB.fxo is using Technique: RegionSB_DX8_VS1_PS14_Norm_Pow 
2026-05-27 09:07:28	RenderEffects\SPL/Region_SB_2UV.fxo is using Technique: RegionSB2UV_DX8_VS1_PS14_Norm_Pow 
2026-05-27 09:07:28	RenderEffects\SPL/Region_GB.fxo is using Technique: RegionGB_DX8_VS1_PS11_NoGlow 
2026-05-27 09:07:28	RenderEffects\SPL/Region_GB_2UV.fxo is using Technique: RegionGB2UV_DX8_VS1_PS11_NoGlow 
2026-05-27 09:07:28	RenderEffects\SPL/Region_RB.fxo is using Technique: RegionRB_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/Region_RB_2UV.fxo is using Technique: RegionRB2UV_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_Basic.fxo is using Technique: SModelBasic_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_Blend.fxo is using Technique: SModelBlnd_DX8_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_BlendNoBump.fxo is using Technique: SModelBlndNoBump_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_Full.fxo is using Technique: SModelFull_DX8_VS1_PS14_Norm_Pow 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_Full_2UV.fxo is using Technique: SModelFull2UV_DX8_VS1_PS14_Norm_Pow 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_Bump.fxo is using Technique: SModelBump_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_Bump_2UV.fxo is using Technique: SModelBump2UV_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_SB.fxo is using Technique: SModelSB_DX8_VS1_PS14_Norm_Pow 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_SB_2UV.fxo is using Technique: SModelSB2UV_DX8_VS1_PS14_Norm_Pow 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_GB.fxo is using Technique: SModelGB_DX8_VS1_PS11 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_GB_2UV.fxo is using Technique: SModelGB2UV_DX8_VS1_PS11_NoGlow 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_RB.fxo is using Technique: SModelRB_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/SModel_RB_2UV.fxo is using Technique: SModelRB2UV_DX8_VS1_PS14 
2026-05-27 09:07:28	RenderEffects\SPL/Terrain_Bump3Detail.fxo is using Technique: RegionC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/Terrain_3Detail.fxo is using Technique: RegionC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/Terrain_Bump2Detail.fxo is using Technique: RegionC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/Terrain_2Detail.fxo is using Technique: RegionC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/Terrain_Bump1Detail.fxo is using Technique: RegionC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/Terrain_1Detail.fxo is using Technique: RegionC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\SPL/Terrain_NoDetail.fxo is using Technique: RegionC1_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\MPL/Terrain_Base.fxo is using Technique: TerrainBase_DX6_VS1_PS0 
2026-05-27 09:07:28	RenderEffects\MPL/Terrain_LightB3SVS1.fxo is using Technique: TerrainLightB3SVS1_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\MPL/Terrain_LightB2SVS1.fxo is using Technique: TerrainLightB2SVS1_DX9_VS1_PS20 
2026-05-27 09:07:28	RenderEffects\MPL/Terrain_LightB1SVS1.fxo is using Technique: TerrainLightB1SVS1_DX9_VS1_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/Terrain_LightVS1.fxo is using Technique: TerrainLightVS1_DX9_VS1_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/Terrain_TextureD3SC1T.fxo is using Technique: TerrainTextureD3SC1T_DX8_VS1_PS14 
2026-05-27 09:07:29	RenderEffects\MPL/Terrain_TextureD2SC1T.fxo is using Technique: TerrainTextureD2SC1T_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/Terrain_TextureD1SC1T.fxo is using Technique: TerrainTextureD1SC1T_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/Terrain_TextureC1T.fxo is using Technique: TerrainTextureC1T_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/Region_Base.fxo is using Technique: RegionBase_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/Region_BaseB.fxo is using Technique: RegionBaseB_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/Region_BaseG.fxo is using Technique: RegionBaseG_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/Region_BaseGA.fxo is using Technique: RegionBaseGA_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/Region_BaseGB.fxo is using Technique: RegionBaseGB_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/Region_Light1.fxo is using Technique: RegionLight1_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/Region_LightB1.fxo is using Technique: RegionLightB1_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/Region_LightBS1.fxo is using Technique: RegionLightBS1_DX9_VS2_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/Region_LightBSF1.fxo is using Technique: RegionLightBSF1_DX9_VS2_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/Region_LightBVS1.fxo is using Technique: RegionLightBVS1_DX9_VS2_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/Region_LightB2VS1.fxo is using Technique: RegionLightB2VS1_DX9_VS2_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD1.fxo is using Technique: RegionTextureD1_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD1T.fxo is using Technique: RegionTextureD1T_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD1C1.fxo is using Technique: RegionTextureD1C1_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD1C1T.fxo is using Technique: RegionTextureD1C1T_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD1C1ST.fxo is using Technique: RegionTextureD1C1ST_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD1R1.fxo is using Technique: RegionTextureD1R1_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD1C1R1T.fxo is using Technique: RegionTextureD1C1R1T_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD1C1SR1T.fxo is using Technique: RegionTextureD1C1SR1T_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/Region_TextureD2C1ST.fxo is using Technique: RegionTextureD2C1ST_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_Base.fxo is using Technique: SModelBase_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_BaseB.fxo is using Technique: SModelBaseB_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_BaseG.fxo is using Technique: SModelBaseG_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_BaseGA.fxo is using Technique: SModelBaseGA_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_BaseGB.fxo is using Technique: SModelBaseGB_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_Light1.fxo is using Technique: SModelLight1_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_LightB1.fxo is using Technique: SModelLightB1_DX8_VS1_PS11_Norm 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_LightBS1.fxo is using Technique: SModelLightBS1_DX9_VS2_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_LightBSF1.fxo is using Technique: SModelLightBSF1_DX9_VS2_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_LightBVS1.fxo is using Technique: SModelLightBVS1_DX9_VS2_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_LightB2VS1.fxo is using Technique: SModelLightB2VS1_DX9_VS2_PS20 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD1.fxo is using Technique: SModelTextureD1_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD1T.fxo is using Technique: SModelTextureD1T_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD1C1.fxo is using Technique: SModelTextureD1C1_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD1C1T.fxo is using Technique: SModelTextureD1C1T_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD1C1ST.fxo is using Technique: SModelTextureD1C1ST_DX6_VS1_PS0 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD1R1.fxo is using Technique: SModelTextureD1R1_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD1C1R1T.fxo is using Technique: SModelTextureD1C1R1T_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD1C1SR1T.fxo is using Technique: SModelTextureD1C1SR1T_DX8_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/SModel_TextureD2C1ST.fxo is using Technique: SModelTextureD2C1ST_DX6_VS1_PS11 
2026-05-27 09:07:29	RenderEffects\MPL/FinalBlend.fxo is using Technique: Final_DX8_VS1_PS11 
2026-05-27 09:07:29	Initializing engine internals.
2026-05-27 09:07:29	CRender::InitDevice completed successfully.
2026-05-27 09:07:29	Display options set, return code 1.
2026-05-27 09:07:29	AutoMipMapping set to 1.
2026-05-27 09:07:29	Camera created.
2026-05-27 09:07:29	Storing display options.
2026-05-27 09:07:29	Initializing fonts.
2026-05-27 09:07:29	Loading string tables.
2026-05-27 09:07:29	Initializing UI.
2026-05-27 09:07:29	Initializing UI manager.
2026-05-27 09:07:29	Initializing fonts.
2026-05-27 09:07:29	Parsing UI XML.
2026-05-27 09:07:29	Loading default UI resources.
2026-05-27 09:07:29	Initializing Music.
2026-05-27 09:07:29	Activating Load Screen.
2026-05-27 09:07:30	Display initialized.
2026-05-27 09:07:30	Initializing global data.
2026-05-27 09:07:30	Loading GlobalFroglok_chr
2026-05-27 09:07:30	Loading GlobalPCFroglok_chr
2026-05-27 09:07:30	Failed to open C:\Program Files (x86)\P1999\GlobalPCFroglok_chr.s3d.
2026-05-27 09:07:30	
2026-05-27 09:07:30	Loading frogequip
2026-05-27 09:07:30	Loading GlobalSKE_chr2
2026-05-27 09:07:30	Loading GlobalDRK_chr
2026-05-27 09:07:30	Failed to open C:\Program Files (x86)\P1999\GlobalDRK_chr.s3d.
2026-05-27 09:07:30	
2026-05-27 09:07:30	Loading Global_obj
2026-05-27 09:07:30	Loading GEquip
2026-05-27 09:07:31	Loading GEquip8
2026-05-27 09:07:31	Loading GEquip2
2026-05-27 09:07:32	Loading grass
2026-05-27 09:07:32	Loading GEquip4
2026-05-27 09:07:32	Loading GEquip3
2026-05-27 09:07:32	Loading loyequip
2026-05-27 09:07:32	Loading ldonequip
2026-05-27 09:07:32	Loading gatesequip
2026-05-27 09:07:32	Loading globalKEM_chr2
2026-05-27 09:07:32	Loading globalKEM_chr
2026-05-27 09:07:33	Loading VEquip
2026-05-27 09:07:33	Loading globalKEF_chr2
2026-05-27 09:07:33	Loading globalKEF_chr
2026-05-27 09:07:35	Loading rap_chr
2026-05-27 09:07:35	Loading skt_chr
2026-05-27 09:07:35	Loading Global4_chr
2026-05-27 09:07:35	Loading Global_chr
2026-05-27 09:07:37	Loading Global17_amr
2026-05-27 09:07:37	Loading Global18_amr
2026-05-27 09:07:37	Loading Global19_amr
2026-05-27 09:07:37	Loading Global20_amr
2026-05-27 09:07:38	Loading Global21_amr
2026-05-27 09:07:38	Loading Global22_amr
2026-05-27 09:07:38	Loading Global23_amr
2026-05-27 09:07:39	Loading Global2_chr
2026-05-27 09:07:39	Loading Global3_chr
2026-05-27 09:07:39	Loading GEquip5
2026-05-27 09:07:39	Loading growthplane_chr
2026-05-27 09:07:39	Loading karnor_chr
2026-05-27 09:07:40	Loading commons_chr
2026-05-27 09:07:40	Initializing sky system.
2026-05-27 09:07:41	Global data initialized.
2026-05-27 09:07:41	Starting process game.
2026-05-27 09:07:41	Starting network game.
2026-05-27 09:07:41	
2026-05-27 09:07:41	Check 1sa. 0xce8a68fb
2026-05-27 09:07:41	
2026-05-27 09:07:41	Check 1x. 0x9e15bc94
2026-05-27 09:07:41	
2026-05-27 09:07:41	Starting load.
2026-05-27 09:07:41	
2026-05-27 09:07:41	Attempting to load load.EQG.
2026-05-27 09:07:41	Verifying world files.
2026-05-27 09:07:41	Loading zone specific files.
2026-05-27 09:07:41	Loading load_obj2
2026-05-27 09:07:41	Loading load_obj
2026-05-27 09:07:41	Loading load_chr2
2026-05-27 09:07:41	Loading load_chr
2026-05-27 09:07:41	Loading load
2026-05-27 09:07:41	Loading objects
2026-05-27 09:07:41	Loading lights
2026-05-27 09:07:41	Initializing cameras.
2026-05-27 09:07:41	Initializing lights.
2026-05-27 09:07:41	Initializing visual effects.
2026-05-27 09:07:41	Initializing target indicator.
2026-05-27 09:07:41	Initializing player path.
2026-05-27 09:07:41	Performing post-load operations.
2026-05-27 09:07:41	Initializing precipitation system.
2026-05-27 09:07:41	World initialized: load
2026-05-27 09:07:41	load done.
2026-05-27 09:07:41	
2026-05-27 09:07:41	Starting char select.
2026-05-27 09:07:41	
2026-05-27 09:07:41	Clearing display buffers.
2026-05-27 09:07:41	
2026-05-27 09:07:41	Display buffers cleared.
2026-05-27 09:07:41	
2026-05-27 09:07:41	Initializing character select UI.
2026-05-27 09:07:41	Resetting game UI.
```


## Char Select

Character select screen loaded

``` text
2026-05-27 07:27:10	Activating Load Screen.
2026-05-27 07:27:22	Starting char select.
2026-05-27 07:27:22	Initializing character select UI.
2026-05-27 07:27:22	Resetting game UI.
```


## Zoning Back In

Logging back into the game or zoning to a new zone

``` text
2026-05-27 07:28:58	ZONING
2026-05-27 07:28:58	Networking: Connection Closed [0] with 0 pending bytes.
2026-05-27 07:28:58	Networking: using port [63246].
2026-05-27 07:28:58	Networking: Connection Established [1]
2026-05-27 07:28:58	Connected to 70.35.159.51:31515...
2026-05-27 07:28:58	
2026-05-27 07:28:58	Zone Connect -- 2 -- Sending MSG_EQ_ADDPLAYER
2026-05-27 07:28:59	Zone Connect -- 3 -- Received MSG_SEND_PC
2026-05-27 07:28:59	Zone Connect -- 4 -- Received MSG_EQ_ADDPLAYER
2026-05-27 07:28:59	Received our EQPlayer from zone. MSG_EQ_NETPLAYERBUFF is next.
2026-05-27 07:28:59	Player = Floppur, zone = City of Mist
2026-05-27 07:29:00	MSG_EQ_NETPLAYERBUFF received started.
2026-05-27 07:29:00	MSG_EQ_NETPLAYERBUFF finished.
2026-05-27 07:29:01	MSG_EQ_NETPLAYERBUFF received started.
2026-05-27 07:29:01	MSG_EQ_NETPLAYERBUFF finished.
2026-05-27 07:29:01	MSG_EQ_NETPLAYERBUFF received started.
2026-05-27 07:29:01	MSG_EQ_NETPLAYERBUFF finished.
2026-05-27 07:29:01	MSG_TIME_STAMP received.
2026-05-27 07:29:01	
2026-05-27 07:29:01	MSG_TIME_STAMP received. (Items inc).
2026-05-27 07:29:01	
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 1
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 3
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 4
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 5
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 6
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 7
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 8
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 9
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 10
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 11
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 12
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 13
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 15
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 16
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 17
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 18
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 19
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 20
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 22
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 23
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 24
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 25
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 26
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 27
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 28
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2000
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2001
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2002
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2003
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2004
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2005
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2006
2026-05-27 07:29:02	Received an item via EQI_STARTING_ITEM at loc 2007
2026-05-27 07:29:02	Item done, MSG_WEATHER_EVENT received.
2026-05-27 07:29:03	
2026-05-27 07:29:03	Initializing zone.
2026-05-27 07:29:03	Initializing world.
2026-05-27 07:29:03	Attempting to load citymist.EQG.
2026-05-27 07:29:03	Verifying world files.
2026-05-27 07:29:03	Loading zone specific files.
2026-05-27 07:29:03	Loading citymist_obj2
2026-05-27 07:29:03	Loading citymist_obj
2026-05-27 07:29:03	Loading citymist_chr2
2026-05-27 07:29:03	Loading citymist_chr
2026-05-27 07:29:03	Loading muh_chr
2026-05-27 07:29:03	Loaded NPC with code muh from muh_chr.s3d
2026-05-27 07:29:03	
2026-05-27 07:29:03	Loading rem_chr
2026-05-27 07:29:03	Loaded NPC with code rem from rem_chr.s3d
2026-05-27 07:29:03	
2026-05-27 07:29:03	Loading citymist
2026-05-27 07:29:03	Loading objects
2026-05-27 07:29:03	Loading lights
2026-05-27 07:29:03	Initializing cameras.
2026-05-27 07:29:03	Initializing lights.
2026-05-27 07:29:03	Initializing visual effects.
2026-05-27 07:29:03	Initializing target indicator.
2026-05-27 07:29:03	Initializing player path.
2026-05-27 07:29:03	Performing post-load operations.
2026-05-27 07:29:03	Initializing precipitation system.
2026-05-27 07:29:03	World initialized: citymist
2026-05-27 07:29:03	Requesting zone data.
2026-05-27 07:29:03	Resetting cameras.
2026-05-27 07:29:03	Resetting vision.
2026-05-27 07:29:03	Resetting overlays.
2026-05-27 07:29:03	Zone initialized.
2026-05-27 07:29:03	Creating INI files.
2026-05-27 07:29:03	Requesting AA data.
2026-05-27 07:29:03	Requesting Skill rank data.
2026-05-27 07:29:03	Loading UI.
2026-05-27 07:29:03	Deactivating previous UI.
2026-05-27 07:29:03	Unloading previous textures.
2026-05-27 07:29:03	Resetting UI.
2026-05-27 07:29:03	Resetting character select UI.
2026-05-27 07:29:03	Resetting game UI.
2026-05-27 07:29:03	UI Reset.
2026-05-27 07:29:03	Initializing UI.
2026-05-27 07:29:03	Initializing UI manager.
2026-05-27 07:29:03	Initializing fonts.
2026-05-27 07:29:03	Parsing UI XML.
2026-05-27 07:29:04	Loading default UI resources.
2026-05-27 07:29:04	Initializing game UI.
2026-05-27 07:29:04	Loading Icons.
2026-05-27 07:29:04	Resetting viewport.
2026-05-27 07:29:04	Game UI Initialized.
2026-05-27 07:29:04	Entering main loop.
2026-05-27 07:29:04	Loading game sounds.
2026-05-27 07:29:04	Requesting initialization data.
2026-05-27 07:29:04	DoMainLoop: just before first while(!ReadyEnterWorld).
2026-05-27 07:29:04	Zone Connect -- Received MSG_READY_ENTER_WORLD
2026-05-27 07:29:04	DoMainLoop: complete after first while(!ReadyEnterWorld).
2026-05-27 07:29:04	DoMainLoop: just before second while(!ReadyEnterWorld).
2026-05-27 07:29:04	Zone Connect -- Sending out a MSG_READY_ENTER_WORLD.
2026-05-27 07:29:05	Zone Connect -- Received MSG_READY_ENTER_WORLD
2026-05-27 07:29:05	DoMainLoop: completed second while(!ReadyEnterWorld).
2026-05-27 07:29:05	Setting up models.
2026-05-27 07:29:05	Setting up character.
2026-05-27 07:29:05	Activating music.
2026-05-27 07:29:05	Initialization complete.
2026-05-27 07:29:05	Entering main loop.
2026-05-27 07:29:08	Item done, MSG_WEATHER_EVENT received.
2026-05-27 07:29:08	
```


## Quitting from character select

Player is at character select and hits the quit button

``` text
2026-05-27 09:05:37	Quitting normally.
2026-05-27 09:05:37	
2026-05-27 09:05:37	Cleanup 1
2026-05-27 09:05:37	
2026-05-27 09:05:37	Cleanup 4
2026-05-27 09:05:37	
2026-05-27 09:05:37	Cleanup 5
2026-05-27 09:05:37	
2026-05-27 09:05:37	Cleanup 6
2026-05-27 09:05:37	
2026-05-27 09:05:37	Cleanup 7
2026-05-27 09:05:37	
2026-05-27 09:05:37	Cleanup 8
2026-05-27 09:05:37	
2026-05-27 09:05:37	Cleanup 9
2026-05-27 09:05:37	
2026-05-27 09:05:37	Cleanup 10
2026-05-27 09:05:37	
2026-05-27 09:05:37	Resetting UI.
2026-05-27 09:05:37	Resetting character select UI.
2026-05-27 09:05:37	Resetting game UI.
2026-05-27 09:05:37	UI Reset.
2026-05-27 09:05:38	Cleanup 11
2026-05-27 09:05:38	
2026-05-27 09:05:38	Picking a default resolution, desktop is 1920 x 1080, 32 bits
2026-05-27 09:05:38	Ratio is 1.78
2026-05-27 09:05:38	Resolution was capped at 1280 x 720
2026-05-27 09:05:38	Resolution verified 1280 x 720, 32 bits ... diff was 1000 from 0 modes
2026-05-27 09:05:38	Resolution selected 1280 x 720, 32 bits
2026-05-27 09:05:38	CRender::InitDevice: Using 32bit mode.
2026-05-27 09:05:38	CRender::InitDevice: Using vsync 0.
2026-05-27 09:05:38	CRender::InitDevice: Using 24bit depth buffer with 8 bit stencil.
2026-05-27 09:05:38	CRender::InitDevice: HardwareTnL Enabled.  
2026-05-27 09:05:38	Using hardware vertex shaders. 
2026-05-27 09:05:38	Initializing render system.
2026-05-27 09:05:38	Trilinear Mipmapping available.
2026-05-27 09:05:38	Vertex Shader Version: 3.0 
2026-05-27 09:05:38	Pixel Shader Version: 3.0 
2026-05-27 09:05:38	Initializing engine internals.
2026-05-27 09:05:38	CRender::InitDevice completed successfully.
2026-05-27 09:05:38	Parsing INI file ./eqlsUIConfig.ini
2026-05-27 09:05:38	INI file ./eqlsUIConfig.ini loaded.
```