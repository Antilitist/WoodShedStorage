--[[
  Wood Shed Storage — 2x2 custom shed + 2x1 lean-to, one bay each.
  Capacity from Sandbox (50-2000, default 400) on build; restored from thumpable
  modData on chunk load so it survives save/quit.

  SpriteConfig ghosts a 2x2 for R-rotate. OnCreate keeps ONE IsoThumpable
  (the open bay) and extra sprites on the other squares — not four lootable boxes.
    S master = woodshed_01_2
    E master = woodshed_01_5
    Lean-to S master = woodshed_01_9
    Lean-to E master = woodshed_01_10
  Do not setContainer(nil). Do not share one ItemContainer across four objects.

  JB Max Capacity Override is OPTIONAL. Sandbox UseJBOverride (default true).
  Detect JB via getActivatedMods (JB's Lua is client-only; require() fails
  on dedicated servers). registerJB() is client-only. Server still writes
  JB_MaxCapacityOverride when the toggle is on and JB is active.
  Requested capacity (50-2000) is saved. Live container is 100 only when
  JB is unused. Turning JB back on restores the requested value.
]]

BuildRecipeCode = BuildRecipeCode or {}
BuildRecipeCode.woodShedStorage = BuildRecipeCode.woodShedStorage or {}

local DEFAULT_CAPACITY = 400
local MIN_CAPACITY = 50
local MAX_CAPACITY = 2000
local VANILLA_MAX_CAPACITY = 100
local CONTAINER_TYPE = "woodshed"
local DISPLAY_NAME = "Wood Shed"

-- JB probe is lazy: sandbox is not ready at file load.
-- Detection uses getActivatedMods (JB Lua is client-only; require fails on dedicated).
local JB_READY = false
local JB_PROBED = false
local printedNoJB = false

local function wantJBOverride()
    -- Default true if the sandbox key is missing (old saves).
    if SandboxVars and SandboxVars.WoodShedStorage and SandboxVars.WoodShedStorage.UseJBOverride == false then
        return false
    end
    return true
end

local function isJBModActive()
    local mods = getActivatedMods and getActivatedMods() or nil
    if not mods then
        return false
    end
    local function isJBId(id)
        id = tostring(id or "")
        return id == "JB_MaxCapacityOverride" or id == "\\JB_MaxCapacityOverride"
    end
    if mods.contains then
        local ok, hit = pcall(function()
            return mods:contains("JB_MaxCapacityOverride") or mods:contains("\\JB_MaxCapacityOverride")
        end)
        if ok and hit then
            return true
        end
    end
    if mods.size then
        local ok, hit = pcall(function()
            for i = 0, mods:size() - 1 do
                if isJBId(mods:get(i)) then
                    return true
                end
            end
            return false
        end)
        if ok and hit then
            return true
        end
    end
    return false
end

local function registerJB()
    -- Client-only. Register type at MAX so per-shed modData can be any sandbox value.
    local ok, JB = pcall(function()
        return require("JB_MaxCapacityOverride")
    end)
    if ok and JB and JB.addContainer then
        pcall(function()
            JB.addContainer(CONTAINER_TYPE, MAX_CAPACITY, true)
        end)
        return true
    end
    return false
end

local function noteNoJB(why)
    if printedNoJB then
        return
    end
    printedNoJB = true
    print("[WoodShedStorage] " .. why .. " — live bay cap 100, requested capacity kept.")
end

-- True when sandbox wants JB AND the mod is in the activated list.
-- registerJB() only on client. Dedicated server still writes JB mod data.
local function usingJB()
    if not wantJBOverride() then
        noteNoJB("UseJBOverride off")
        return false
    end
    if not JB_PROBED then
        JB_PROBED = true
        JB_READY = isJBModActive()
        if JB_READY then
            local server = false
            pcall(function()
                server = isServer() == true
            end)
            if not server then
                local registered = registerJB()
                print("[WoodShedStorage] JB active type='" .. CONTAINER_TYPE
                    .. "' max=" .. tostring(MAX_CAPACITY)
                    .. " registered=" .. tostring(registered))
            else
                print("[WoodShedStorage] JB active on server — writing JB mod data, skip client register")
            end
        else
            noteNoJB("JB_MaxCapacityOverride not found")
        end
    end
    if not JB_READY then
        noteNoJB("JB_MaxCapacityOverride not found")
    end
    return JB_READY
end

-- Always 50-2000. This is what we persist.
local function clampRequested(cap)
    cap = tonumber(cap) or DEFAULT_CAPACITY
    if cap < MIN_CAPACITY then
        cap = MIN_CAPACITY
    end
    if cap > MAX_CAPACITY then
        cap = MAX_CAPACITY
    end
    return math.floor(cap)
end

-- Live container only. 100 when JB is unused; requested otherwise.
local function liveCapacity(requested)
    requested = clampRequested(requested)
    if usingJB() then
        return requested
    end
    if requested > VANILLA_MAX_CAPACITY then
        return VANILLA_MAX_CAPACITY
    end
    return requested
end

local function getSandboxCapacity()
    local cap = DEFAULT_CAPACITY
    if SandboxVars and SandboxVars.WoodShedStorage and SandboxVars.WoodShedStorage.Capacity ~= nil then
        cap = SandboxVars.WoodShedStorage.Capacity
    end
    return clampRequested(cap)
end

local function applyCapacity(thumpable, capacity, reason)
    local jb = usingJB()
    local requested = clampRequested(capacity)
    local live = liveCapacity(requested)

    if thumpable.setName then
        thumpable:setName(DISPLAY_NAME)
    end

    local md = thumpable:getModData()
    md.WoodShedStorage = true
    md.woodShedBay = true
    md.woodShedCapacity = requested
    -- JB reads this from the parent object (thumpable), not the container.
    -- Do not write it when JB is unused, or leftover data can re-inflate the bay.
    if jb then
        md["JB_MaxCapacityOverride"] = { capacity = requested }
    else
        md["JB_MaxCapacityOverride"] = nil
    end

    if not thumpable:getContainer() then
        thumpable:setContainer(ItemContainer.new())
    end

    local c = thumpable:getContainer()
    if not c then
        print("[WoodShedStorage] WARNING: no container (" .. tostring(reason) .. ")")
        return false
    end

    if c.setType then
        c:setType(CONTAINER_TYPE)
    end

    if c.getModData then
        if jb then
            c:getModData()["JB_MaxCapacityOverride"] = { capacity = requested }
        else
            c:getModData()["JB_MaxCapacityOverride"] = nil
        end
    end

    if c.setCapacity then
        c:setCapacity(live)
    end

    local actual = c.getCapacity and c:getCapacity() or "?"
    print("[WoodShedStorage] capacity applied reason=" .. tostring(reason)
        .. " requested=" .. tostring(requested)
        .. " live=" .. tostring(live)
        .. " actual=" .. tostring(actual)
        .. " jb=" .. tostring(jb))
    return true
end

local function spriteNameOf(obj)
    if not obj or not obj.getSprite or not obj:getSprite() then
        return ""
    end
    return tostring(obj:getSprite():getName() or "")
end

local function isShedSprite(name)
    return type(name) == "string" and string.sub(name, 1, 12) == "woodshed_01_"
end

local function isMasterSprite(name)
    return name == "woodshed_01_2" or name == "woodshed_01_5"
        or name == "woodshed_01_9" or name == "woodshed_01_10"
end

local function isLeanMaster(name)
    return name == "woodshed_01_9" or name == "woodshed_01_10"
end

-- Extra sprites around the one IsoThumpable (chicken-hutch extraSprites style).
-- dx = east, dy = south. Master sits on the open bay square.
local EXTRAS = {
    ["woodshed_01_2"] = { -- S, master = SW
        { sprite = "woodshed_01_0", dx = 0, dy = -1 },
        { sprite = "woodshed_01_1", dx = 1, dy = -1 },
        { sprite = "woodshed_01_3", dx = 1, dy = 0 },
    },
    ["woodshed_01_5"] = { -- E, master = NE
        { sprite = "woodshed_01_4", dx = -1, dy = 0 },
        { sprite = "woodshed_01_6", dx = -1, dy = 1 },
        { sprite = "woodshed_01_7", dx = 0, dy = 1 },
    },
    ["woodshed_01_9"] = { -- lean-to S, master = east tile
        { sprite = "woodshed_01_8", dx = -1, dy = 0 },
    },
    ["woodshed_01_10"] = { -- lean-to E, master = north tile
        { sprite = "woodshed_01_11", dx = 0, dy = 1 },
    },
}

local pendingMasters = {}
local armTickSweep = function() end

local function squareHasWoodShed(sq)
    if not sq or not sq.getObjects then
        return false
    end
    local objs = sq:getObjects()
    for i = 0, objs:size() - 1 do
        local obj = objs:get(i)
        local n = spriteNameOf(obj)
        if isShedSprite(n) then
            return true
        end
        local md = obj.getModData and obj:getModData() or nil
        if md and md.WoodShedExtra then
            return true
        end
    end
    return false
end

local function disableOutline(obj)
    if not obj then
        return
    end
    pcall(function()
        if obj.setOutlineOnMouseover then
            obj:setOutlineOnMouseover(false)
        end
    end)
    pcall(function()
        if obj.setOutlineHighlight then
            obj:setOutlineHighlight(false)
        end
    end)
end

local function placeExtraSprite(master, extra)
    local msq = master:getSquare()
    if not msq then
        return
    end
    local cell = getCell and getCell() or nil
    if not cell then
        return
    end
    local sq = cell:getGridSquare(msq:getX() + extra.dx, msq:getY() + extra.dy, msq:getZ())
    if not sq then
        return
    end
    if squareHasWoodShed(sq) then
        return
    end
    local obj = nil
    pcall(function()
        obj = IsoObject.new(cell, sq, extra.sprite)
    end)
    if not obj then
        pcall(function()
            obj = IsoObject.new(sq, extra.sprite)
        end)
    end
    if not obj then
        print("[WoodShedStorage] extra sprite failed " .. tostring(extra.sprite))
        return
    end
    local md = obj:getModData()
    md.WoodShedExtra = true
    md.woodShedMasterX = msq:getX()
    md.woodShedMasterY = msq:getY()
    md.woodShedMasterZ = msq:getZ()
    disableOutline(obj)
    sq:AddSpecialObject(obj)
    pcall(function()
        obj:transmitCompleteItemToClients()
    end)
    print("[WoodShedStorage] extra sprite " .. extra.sprite
        .. " at " .. tostring(sq:getX()) .. "," .. tostring(sq:getY()))
end

local function placeExtras(master)
    local name = spriteNameOf(master)
    local list = EXTRAS[name]
    if not list then
        return
    end
    for i = 1, #list do
        placeExtraSprite(master, list[i])
    end
end

local function removeExtraThumpable(thumpable)
    local sq = thumpable.getSquare and thumpable:getSquare() or nil
    pcall(function()
        thumpable:removeFromWorld()
    end)
    pcall(function()
        thumpable:removeFromSquare()
    end)
    -- Do not transmitRemoveItemFromSquare here: Java looks for SpriteConfig siblings.
    pcall(function()
        if sq and sq.RemoveTileObject then
            sq:RemoveTileObject(thumpable)
        end
    end)
    pcall(function()
        thumpable:setSquare(nil)
    end)
end

local RECIPE_DROPS = {
    { "Base.Plank", 10 },
    { "Base.Nails", 10 },
    { "Base.Log", 6 },
}

local LEAN_DROPS = {
    { "Base.Plank", 8 },
    { "Base.Nails", 8 },
    { "Base.Log", 4 },
}

-- Dump loot without IsoObjectUtils.dumpContentsInSquare (that WARNs on 2x2 SpriteConfig).
local function dumpShedContents(master)
    if not master then
        return
    end
    local sq = master.getSquare and master:getSquare() or nil
    local c = master.getContainer and master:getContainer() or nil
    if not sq or not c or not c.getItems then
        return
    end
    local items = c:getItems()
    if not items then
        return
    end
    for i = items:size() - 1, 0, -1 do
        local item = items:get(i)
        pcall(function()
            c:Remove(item)
            sq:AddWorldInventoryItem(item, 0.0, 0.0, 0.0)
        end)
    end
end

local function dropBuildMats(master)
    local sq = master and master.getSquare and master:getSquare() or nil
    if not sq then
        return
    end
    local dropped = false
    pcall(function()
        if master.getBuildMaterials then
            local mats = master:getBuildMaterials()
            if mats then
                for typ, v in pairs(mats) do
                    local max = tonumber(v) or 1
                    local count = ZombRand(max) + 1
                    for _ = 1, count do
                        sq:AddWorldInventoryItem(typ, 0, 0, 0)
                    end
                    dropped = true
                end
            end
        end
    end)
    if dropped then
        return
    end
    local drops = RECIPE_DROPS
    if isLeanMaster(spriteNameOf(master)) then
        drops = LEAN_DROPS
    end
    for i = 1, #drops do
        local typ = drops[i][1]
        local max = drops[i][2]
        local count = ZombRand(max) + 1
        for _ = 1, count do
            sq:AddWorldInventoryItem(typ, 0, 0, 0)
        end
    end
end

local function stealContainerItems(fromObj, toObj)
    local fromC = fromObj and fromObj.getContainer and fromObj:getContainer() or nil
    local toC = toObj and toObj.getContainer and toObj:getContainer() or nil
    if not fromC or not toC or fromC == toC then
        return
    end
    local items = fromC.getItems and fromC:getItems() or nil
    if not items then
        return
    end
    for i = items:size() - 1, 0, -1 do
        local item = items:get(i)
        pcall(function()
            fromC:Remove(item)
            toC:AddItem(item)
        end)
    end
end

-- SpriteConfig 2x2 stays in Java until we replace the master with a plain IsoThumpable.
local function replaceWithPlainMaster(thumpable)
    local sq = thumpable.getSquare and thumpable:getSquare() or nil
    if not sq then
        return thumpable
    end
    local spriteName = spriteNameOf(thumpable)
    local north = false
    pcall(function()
        north = thumpable:getNorth() == true
    end)
    local cell = getCell()
    local newObj = nil
    pcall(function()
        newObj = IsoThumpable.new(cell, sq, spriteName, north, {})
    end)
    if not newObj then
        pcall(function()
            newObj = IsoThumpable.new(getCell(), sq, spriteName, north, thumpable)
        end)
    end
    if not newObj then
        print("[WoodShedStorage] plain IsoThumpable failed, keeping SpriteConfig master")
        return thumpable
    end
    pcall(function()
        sq:AddSpecialObject(newObj)
    end)
    applyCapacity(newObj, getSandboxCapacity(), "OnCreate-plain")
    stealContainerItems(thumpable, newObj)
    pcall(function()
        if thumpable.getMaxHealth then
            newObj:setMaxHealth(thumpable:getMaxHealth())
            newObj:setHealth(thumpable:getHealth())
        end
    end)
    pcall(function()
        newObj:setIsDismantable(true)
        newObj:setName(DISPLAY_NAME)
        newObj:setIsThumpable(true)
        newObj:setBlockAllTheSquare(true)
        newObj:setCanBeLockByPadlock(true)
        newObj:setExplored(true)
    end)
    removeExtraThumpable(thumpable)
    print("[WoodShedStorage] replaced SpriteConfig master with plain IsoThumpable")
    return newObj
end

function BuildRecipeCode.woodShedStorage.OnCreate(params)
    print("[WoodShedStorage] OnCreate fired")
    local thumpable = params and params.thumpable
    if not thumpable then
        print("[WoodShedStorage] OnCreate: no thumpable")
        return
    end

    local result = nil
    local ok, err = pcall(function()
        local spriteName = spriteNameOf(thumpable)
        print("[WoodShedStorage] sprite=" .. spriteName)
        if isMasterSprite(spriteName) then
            local master = replaceWithPlainMaster(thumpable)
            pcall(function()
                if master.setIsDismantable then
                    master:setIsDismantable(true)
                end
            end)
            placeExtras(master)
            pendingMasters[#pendingMasters + 1] = master
            armTickSweep()
            if master ~= thumpable then
                result = { replaceObject = true, object = master }
            end
        elseif isShedSprite(spriteName) then
            -- Other three SpriteConfig cells: drop the extra IsoThumpable.
            -- Visual/collision is an extra sprite owned via WoodShedExtra, not a second box.
            removeExtraThumpable(thumpable)
            result = { objectAlreadyTransmitted = true }
        end
    end)

    if not ok then
        print("[WoodShedStorage] OnCreate error: " .. tostring(err))
    end
    return result
end

local function findMasterFromExtra(obj)
    local md = obj and obj.getModData and obj:getModData() or nil
    if not md or not md.WoodShedExtra then
        return nil
    end
    local cell = getCell and getCell() or nil
    if not cell then
        return nil
    end
    local sq = cell:getGridSquare(md.woodShedMasterX, md.woodShedMasterY, md.woodShedMasterZ)
    if not sq or not sq.getObjects then
        return nil
    end
    local objs = sq:getObjects()
    for i = 0, objs:size() - 1 do
        local o = objs:get(i)
        if isMasterSprite(spriteNameOf(o)) then
            return o
        end
    end
    return nil
end

local function getShedMaster(obj)
    if not obj then
        return nil
    end
    local name = spriteNameOf(obj)
    if isMasterSprite(name) then
        return obj
    end
    local md = obj.getModData and obj:getModData() or nil
    if md and md.WoodShedExtra then
        return findMasterFromExtra(obj)
    end
    if isShedSprite(name) then
        -- leftover 1.2.x extra thumpable: look around
        local sq = obj.getSquare and obj:getSquare() or nil
        if sq then
            local x, y, z = sq:getX(), sq:getY(), sq:getZ()
            local cell = getCell()
            for dx = -1, 1 do
                for dy = -1, 1 do
                    local nsq = cell and cell:getGridSquare(x + dx, y + dy, z)
                    if nsq and nsq.getObjects then
                        local objs = nsq:getObjects()
                        for i = 0, objs:size() - 1 do
                            local o = objs:get(i)
                            if isMasterSprite(spriteNameOf(o)) then
                                return o
                            end
                        end
                    end
                end
            end
        end
    end
    return nil
end

local function footprintSquares(master)
    local list = {}
    local sq = master and master.getSquare and master:getSquare()
    if sq then
        list[#list + 1] = sq
    end
    local extras = EXTRAS[spriteNameOf(master)]
    if extras and sq then
        local cell = getCell()
        for i = 1, #extras do
            local e = extras[i]
            local nsq = cell and cell:getGridSquare(sq:getX() + e.dx, sq:getY() + e.dy, sq:getZ())
            if nsq then
                list[#list + 1] = nsq
            end
        end
    end
    return list
end

local function playerCanReachShed(playerObj, master)
    if not playerObj or not master then
        return false
    end
    local playerSq = playerObj:getCurrentSquare()
    if not playerSq then
        return false
    end
    local squares = footprintSquares(master)
    for i = 1, #squares do
        local sq = squares[i]
        if playerSq:getZ() == sq:getZ()
            and math.abs(playerSq:getX() - sq:getX()) <= 1
            and math.abs(playerSq:getY() - sq:getY()) <= 1 then
            local blocked = false
            pcall(function()
                blocked = playerSq:isBlockedTo(sq) == true
            end)
            if not blocked then
                return true
            end
        end
        local adj = false
        pcall(function()
            adj = AdjacentFreeTileFinder.isTileOrAdjacent(playerSq, sq) == true
        end)
        if adj then
            return true
        end
    end
    return false
end

local function openShedLoot(playerObj, master, x, y)
    local container = nil
    if master.getContainerClickedOn and x and y then
        pcall(function()
            container = master:getContainerClickedOn(x, y)
        end)
    end
    if not container then
        container = master.getContainer and master:getContainer() or nil
    end
    if not container then
        return
    end
    if not container:isExplored() then
        if not isClient() then
            ItemPicker.fillContainer(container, playerObj)
        else
            container:requestServerItemsForContainer()
        end
        container:setExplored(true)
    end
    local panel2 = getPlayerLoot(0)
    if not panel2 then
        return
    end
    panel2:setNewContainer(container)
    panel2:setVisible(true)
    panel2.collapseCounter = 0
    if panel2.isCollapsed then
        panel2.isCollapsed = false
        panel2:clearMaxDrawHeight()
        panel2.collapseCounter = -30
    end
end

-- Restore capacity on the one master. Never setContainer(nil).
local function onLoadGridsquare(square)
    if not square or not square.getObjects then
        return
    end
    local objects = square:getObjects()
    if not objects then
        return
    end
    for i = 0, objects:size() - 1 do
        local obj = objects:get(i)
        local name = spriteNameOf(obj)
        if isMasterSprite(name) then
            local md = obj.getModData and obj:getModData() or nil
            local cap = md and md.woodShedCapacity or nil
            if not cap and md and md["JB_MaxCapacityOverride"] and md["JB_MaxCapacityOverride"].capacity then
                cap = md["JB_MaxCapacityOverride"].capacity
            end
            if not cap then
                cap = getSandboxCapacity()
            end
            local requested = clampRequested(cap)
            local jb = usingJB()
            local live = liveCapacity(requested)
            local need = true
            local c = obj.getContainer and obj:getContainer() or nil
            local actual = c and c.getCapacity and c:getCapacity() or nil
            local jbMd = md and md["JB_MaxCapacityOverride"] or nil
            local jbCap = jbMd and jbMd.capacity or nil
            if md and md.WoodShedStorage and md.woodShedCapacity == requested and actual == live then
                if jb then
                    if jbCap == requested then
                        need = false
                    end
                elseif not jbMd then
                    need = false
                end
            end
            if need then
                pcall(function()
                    applyCapacity(obj, requested, "LoadGridsquare")
                end)
            end
        elseif obj.getModData and obj:getModData() and obj:getModData().WoodShedExtra then
            disableOutline(obj)
        end
    end
end

Events.LoadGridsquare.Add(onLoadGridsquare)

local wipingShed = false

local function isShedWorldObject(obj)
    if not obj then
        return false
    end
    local name = spriteNameOf(obj)
    if isShedSprite(name) then
        return true
    end
    local md = obj.getModData and obj:getModData() or nil
    return md and (md.WoodShedExtra or md.WoodShedStorage) or false
end

local function removeWorldObject(obj)
    if not obj then
        return
    end
    local sq = obj.getSquare and obj:getSquare() or nil
    pcall(function()
        if sq and sq.transmitRemoveItemFromSquare then
            sq:transmitRemoveItemFromSquare(obj)
        end
    end)
    pcall(function()
        if sq and sq.RemoveTileObject then
            sq:RemoveTileObject(obj)
        end
    end)
    pcall(function()
        if obj.removeFromWorld then
            obj:removeFromWorld()
        end
    end)
    pcall(function()
        if obj.removeFromSquare then
            obj:removeFromSquare()
        end
    end)
end

-- Any woodshed_01_* or WoodShedExtra in a 5x5 around origin. Never sledgeDestroy
-- (that can turn the floor into blends_natural dirt / a "cellar hole").
local function wipeEntireShed(origin, keepObj)
    if wipingShed or not origin then
        return
    end
    local originSq = origin.getSquare and origin:getSquare() or nil
    if not originSq then
        return
    end
    wipingShed = true
    local cell = getCell()
    local ox, oy, oz = originSq:getX(), originSq:getY(), originSq:getZ()
    local toRemove = {}
    for dx = -2, 2 do
        for dy = -2, 2 do
            local sq = cell and cell:getGridSquare(ox + dx, oy + dy, oz)
            if sq and sq.getObjects then
                local objs = sq:getObjects()
                for i = 0, objs:size() - 1 do
                    local o = objs:get(i)
                    if o ~= keepObj and isShedWorldObject(o) then
                        toRemove[#toRemove + 1] = o
                    end
                end
            end
        end
    end
    for i = 1, #toRemove do
        removeWorldObject(toRemove[i])
    end
    wipingShed = false
end

Events.OnObjectAboutToBeRemoved.Add(function(obj)
    if wipingShed then
        return
    end
    if not isShedWorldObject(obj) then
        return
    end
    -- Hit ANY shed piece (master, extra sprite, leftover thumpable) → whole 2x2 goes.
    wipeEntireShed(obj, obj)
end)

local function sweepLeftoverThumpables(master)
    local sq = master and master.getSquare and master:getSquare()
    if not sq then
        return
    end
    local cell = getCell()
    local x, y, z = sq:getX(), sq:getY(), sq:getZ()
    for dx = -2, 2 do
        for dy = -2, 2 do
            local nsq = cell and cell:getGridSquare(x + dx, y + dy, z)
            if nsq and nsq.getObjects then
                local objs = nsq:getObjects()
                for i = objs:size() - 1, 0, -1 do
                    local o = objs:get(i)
                    if o ~= master and instanceof(o, "IsoThumpable") then
                        local n = spriteNameOf(o)
                        if isShedSprite(n) and not isMasterSprite(n) then
                            removeExtraThumpable(o)
                        end
                    end
                end
            end
        end
    end
    placeExtras(master)
end

local function wrapClicks()
    if isServer() then
        return
    end
    if not ISObjectClickHandler or not ISObjectClickHandler.doClick then
        return
    end
    if ISObjectClickHandler._woodShedWrapped then
        return
    end
    local old = ISObjectClickHandler.doClick
    ISObjectClickHandler.doClick = function(object, x, y)
        local master = getShedMaster(object)
        if master and master.getContainer and master:getContainer() then
            local playerObj = getSpecificPlayer(0)
            if playerObj and not playerObj:isAiming() and playerCanReachShed(playerObj, master) then
                if instanceof(master, "IsoThumpable") and master.isLockedToCharacter
                    and master:isLockedToCharacter(playerObj) then
                    return
                end
                openShedLoot(playerObj, master, x, y)
                return
            end
        end
        return old(object, x, y)
    end
    ISObjectClickHandler._woodShedWrapped = true
end

local function wrapDisassembleMenu()
    if isServer() then
        return
    end
    if not ISDisassembleMenu or not ISDisassembleMenu.createMenu then
        return
    end
    if ISDisassembleMenu._woodShedWrapped then
        return
    end
    local old = ISDisassembleMenu.createMenu
    ISDisassembleMenu.createMenu = function(worldObjects, context, playerObj)
        -- Right-click extra sprites still offer Disassemble once, on the master.
        if worldObjects then
            local master = nil
            for i = 1, #worldObjects do
                master = getShedMaster(worldObjects[i])
                if master then
                    break
                end
            end
            if master then
                local found = false
                for i = 1, #worldObjects do
                    if worldObjects[i] == master then
                        found = true
                        break
                    end
                end
                if not found then
                    local copy = {}
                    for i = 1, #worldObjects do
                        copy[i] = worldObjects[i]
                    end
                    copy[#copy + 1] = master
                    worldObjects = copy
                end
            end
        end
        return old(worldObjects, context, playerObj)
    end
    ISDisassembleMenu._woodShedWrapped = true
end

Events.OnGameStart.Add(wrapClicks)
Events.OnGameStart.Add(wrapDisassembleMenu)

local function finishShedScrap(obj, character)
    local master = getShedMaster(obj) or obj
    dumpShedContents(master)
    dropBuildMats(master)
    wipeEntireShed(master, nil)
    pcall(function()
        if character then
            addSound(character, character:getX(), character:getY(), character:getZ(), 10, 5)
        end
    end)
end

local function wrapDestroyAndScrap()
    if ISDestroyStuffAction and ISDestroyStuffAction.complete and not ISDestroyStuffAction._woodShedWrapped then
        local oldDestroy = ISDestroyStuffAction.complete
        ISDestroyStuffAction.complete = function(self)
            if self.item and isShedWorldObject(self.item) then
                finishShedScrap(self.item, self.character)
                return true
            end
            return oldDestroy(self)
        end
        ISDestroyStuffAction._woodShedWrapped = true
    end

    if ISDismantleAction and ISDismantleAction.complete and not ISDismantleAction._woodShedWrapped then
        local oldDismantle = ISDismantleAction.complete
        ISDismantleAction.complete = function(self)
            if self.thumpable and isShedWorldObject(self.thumpable) then
                finishShedScrap(self.thumpable, self.character)
                return true
            end
            return oldDismantle(self)
        end
        ISDismantleAction._woodShedWrapped = true
    end

    if ISThumpableSpriteProps and ISThumpableSpriteProps.scrapObjectViaCursor
        and not ISThumpableSpriteProps._woodShedWrapped then
        local oldScrap = ISThumpableSpriteProps.scrapObjectViaCursor
        ISThumpableSpriteProps.scrapObjectViaCursor = function(self, _character, _square, _origSpriteName, _moveCursor)
            if self.object and isShedWorldObject(self.object) then
                finishShedScrap(self.object, _character)
                if _moveCursor then
                    _moveCursor:clearCache()
                end
                return
            end
            return oldScrap(self, _character, _square, _origSpriteName, _moveCursor)
        end
        ISThumpableSpriteProps._woodShedWrapped = true
    end

    -- THIS is the Disassemble menu path (ISMoveablesAction mode "scrap").
    if ISMoveableSpriteProps and ISMoveableSpriteProps.scrapObjectViaCursor
        and not ISMoveableSpriteProps._woodShedScrapWrapped then
        local oldCursor = ISMoveableSpriteProps.scrapObjectViaCursor
        ISMoveableSpriteProps.scrapObjectViaCursor = function(self, _character, _square, _origSpriteName, _moveCursor)
            if self.object and isShedWorldObject(self.object) then
                finishShedScrap(self.object, _character)
                if _moveCursor then
                    _moveCursor:clearCache()
                end
                return
            end
            return oldCursor(self, _character, _square, _origSpriteName, _moveCursor)
        end
        ISMoveableSpriteProps._woodShedScrapWrapped = true
    end

    if ISMoveableSpriteProps and ISMoveableSpriteProps.scrapObject
        and not ISMoveableSpriteProps._woodShedScrapObjectWrapped then
        local oldScrapObj = ISMoveableSpriteProps.scrapObject
        ISMoveableSpriteProps.scrapObject = function(self, _character)
            if self.object and isShedWorldObject(self.object) then
                finishShedScrap(self.object, _character)
                return
            end
            return oldScrapObj(self, _character)
        end
        ISMoveableSpriteProps._woodShedScrapObjectWrapped = true
    end

    if ISMoveablesAction and ISMoveablesAction.complete and not ISMoveablesAction._woodShedWrapped then
        local oldComplete = ISMoveablesAction.complete
        ISMoveablesAction.complete = function(self)
            if self.mode == "scrap" and self.moveProps and self.moveProps.object
                and isShedWorldObject(self.moveProps.object) then
                finishShedScrap(self.moveProps.object, self.character)
                return true
            end
            return oldComplete(self)
        end
        ISMoveablesAction._woodShedWrapped = true
    end
end

Events.OnGameStart.Add(wrapDestroyAndScrap)

if Events.OnTick then
    local n = 0
    local tickArmed = false
    local function tickSweep()
        n = n + 1
        wrapDisassembleMenu()
        wrapDestroyAndScrap()
        if #pendingMasters > 0 then
            local list = pendingMasters
            pendingMasters = {}
            n = 0
            for i = 1, #list do
                pcall(function()
                    sweepLeftoverThumpables(list[i])
                end)
            end
        end
        if n >= 120 then
            Events.OnTick.Remove(tickSweep)
            tickArmed = false
        end
    end
    armTickSweep = function()
        if tickArmed then
            n = 0
            return
        end
        tickArmed = true
        n = 0
        Events.OnTick.Add(tickSweep)
    end
    armTickSweep()
end

print("[WoodShedStorage] BuildRecipeCode.woodShedStorage loaded (one IsoThumpable + extra sprites).")

