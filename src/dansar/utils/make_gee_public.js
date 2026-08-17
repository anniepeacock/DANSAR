var folder = 'projects/project_name/assets/folder_name';

// Make folder public
var folderAcl = ee.data.getAssetAcl(folder);
folderAcl.all_users_can_read = true;
ee.data.setAssetAcl(folder, folderAcl);

print('Folder made public:', folder);

// Make all assets in the folder public
var result = ee.data.listAssets(folder);

var assets = result.assets || [];

print('Found assets:', assets.length);

assets.forEach(function(asset) {
  var assetId = asset.id;

  print('Making public:', assetId);

  var acl = ee.data.getAssetAcl(assetId);
  acl.all_users_can_read = true;

  ee.data.setAssetAcl(assetId, acl);
});

print('Done.');