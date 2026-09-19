--[[
  Wood Shed Storage — place hook via BuildRecipeCode (vanilla path).
  Uses camping log-pile tiles that are known to exist in B42.
]]

BuildRecipeCode = BuildRecipeCode or {}
BuildRecipeCode.woodShedStorage = BuildRecipeCode.woodShedStorage or {}

local CAPACITY = 250

function BuildRecipeCode.woodShedStorage.OnCreate(params)
    print("[WoodShedStorage] OnCreate fired")
    local thumpable = params and params.thumpable
    if not thumpable then
        print("[WoodShedStorage] OnCreate: no thumpable")
        return
    end

    local ok, err = pcall(function()
        local spriteName = ""
        if thumpable.getSprite and thumpable:getSprite() then
            spriteName = tostring(thumpable:getSprite():getName() or "")
        end
        print("[WoodShedStorage] sprite=" .. spriteName)

        if not thumpable:getContainer() then
            thumpable:setContainer(ItemContainer.new())
            print("[WoodShedStorage] created ItemContainer")
        end

        local c = thumpable:getContainer()
        if c and c.setCapacity then
            c:setCapacity(CAPACITY)
            print("[WoodShedStorage] capacity=" .. tostring(CAPACITY))
        else
            print("[WoodShedStorage] WARNING: no container after create")
        end
    end)

    if not ok then
        print("[WoodShedStorage] OnCreate error: " .. tostring(err))
    end
end

-- Alias kept for older entity scripts
WoodShedStorageCode = WoodShedStorageCode or {}
WoodShedStorageCode.OnCreate = BuildRecipeCode.woodShedStorage.OnCreate

print("[WoodShedStorage] WoodShedStorageCode loaded (BuildRecipeCode.woodShedStorage).")
