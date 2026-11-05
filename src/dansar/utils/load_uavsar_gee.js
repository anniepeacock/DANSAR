// Load UAVSAR image
var image = ee.Image(
  'projects/linear-reporter-253320/assets/bigsur_14072_25007_008_250305_L090_CX_01'
);

// Calculate stats 
var stats = image.reduceRegion({
  reducer: ee.Reducer.percentile([95]),
  geometry: image.geometry(),
  scale: 10,
  maxPixels: 1e9
});
print('95 percentile', stats);
print('bands', image.bandNames());
print('projection', image.projection());

// Visualize UAVSAR local incidence angle
Map.addLayer(image.select(['INC']),{min: [0],max: [90]},'UAVSAR INC');
// Visualize UAVSAR mask (1=valid, 2=invalid_incidence_angle, 3=no_data)
// Create a version of the MASK band where 3 (no data) is transparent
var maskVisual = image.select('MASK').updateMask(image.select('MASK').neq(3));
Map.addLayer(maskVisual, {min: 1, max: 2, palette: ['white', 'black']}, 'UAVSAR MASK (3 Transparent)');

// Visualize UAVSAR RGB
Map.centerObject(image, 10);
Map.addLayer(
  image.select(['HH', 'HV', 'VV']),
  {min: [0.0001, 0.0001, 0.0001],
    max: [0.4,    0.1,    0.4]
  },
  'UAVSAR RGB'
);

var bands = image.bandNames();
bands.evaluate(function(bandList) {
  bandList.forEach(function(bandName) {
    var band = image.select(bandName);
    var hist = band.reduceRegion({
      reducer: ee.Reducer.fixedHistogram(0, 1, 100),
      geometry: image.geometry(),
      scale: 20,
      maxPixels: 1e8
    });
    var histData = hist.get(bandName);
    histData.evaluate(function(result) {
      if (result === null || result.length === 0) {
        print('No valid histogram data for: ' + bandName);
        return;
      }

      var histArray = ee.Array(result);
      var x = histArray.slice(1, 0, 1).project([0]);
      var y = histArray.slice(1, 1, 2).project([0]);

      var chart = ui.Chart.array.values({
        array: y,
        axis: 0,
        xLabels: x
      })
      .setChartType('ColumnChart')
      .setOptions({
        title: bandName + ' histogram',
        hAxis: {
          title: 'Backscatter (linear)',
          viewWindow: {
            min: 0,
            max: 1
          }
        },
        vAxis: {
          title: 'Pixel count',
          viewWindow: {min: 0}
        },
        legend: {position: 'none'},
        bar: {groupWidth: '100%'}
      });
      print(chart);
    });
  });
});

