function onOpen() { 
  DocumentApp.getUi()
    .createMenu('Story Map')
    .addItem('Generate Map', 'showSidebarNew')
    .addItem('Show Last Map', 'showSidebarPrevious')
    .addToUi();
}

function setApiUrl(url) {
  PropertiesService.getScriptProperties().setProperty('API_URL', 'https://your-api-url');
}

function getApiUrl() {
  return PropertiesService.getScriptProperties().getProperty('API_URL');
}

function getStoryMapFolder() {
  const folderName = 'Story Maps';
  const folders = DriveApp.getFoldersByName(folderName);
  return folders.hasNext() ? folders.next() : DriveApp.createFolder(folderName);
}

function generateMap() {
  const doc = DocumentApp.getActiveDocument();
  const text = doc.getBody().getText(); 
  const payload = {
    content: text
  };

  const apiUrl = getApiUrl();
  const response = UrlFetchApp.fetch(`${apiUrl}/generate_map`, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(payload)
  });


  const data = JSON.parse(response.getContentText());

  const pngBase64 = data.map_png_base64;
  const conflicts = data.conflicts;
  
  clearAllHighlights();
  PropertiesService.getScriptProperties().setProperty('hue', '-20');
  highlightConflictPairs(conflicts);

  // let blob = response.getBlob();
  // blob.setContentType('image/png');

  const blob = Utilities.newBlob(
    Utilities.base64Decode(pngBase64),
    'image/png',
    'map.png'
  );

  // const folder = getStoryMapFolder();

  // const existingFiles = folder.getFiles();
  // let count = 0;
  // while (existingFiles.hasNext()) { // Taking the count is going to be problematic if I delete things
  //   existingFiles.next();
  //   count++;
  // }

  // const nextNum = count + 1;
  // const fileName = `StoryMap_${nextNum}.png`;

  // const file = folder.createFile(blob).setName(fileName);

  const base64 = Utilities.base64Encode(blob.getBytes());
  return {
    dataUrl: `data:image/png;base64,${base64}`,
    // fileName: fileName,
    // folderUrl: folder.getUrl(),
    fileName: "test",
    folderUrl: "test",
    conflicts: conflicts || []
  };
}

function highlightConflictPairs(conflictPairs) {
  const body = DocumentApp.getActiveDocument().getBody();

  // Generate a new color per pair
  for (let i = 0; i < conflictPairs.length; i++) {
    const [sentA, sentB] = conflictPairs[i];

    // Pick color for this pair
    const color = getNextColor(); // generate unique color per pair

    highlightSentence(body, sentA, color);
    highlightSentence(body, sentB, color);
  }
}

function clearAllHighlights() {
  const body = DocumentApp.getActiveDocument().getBody();
  const textElements = getAllTextElements(body);

  textElements.forEach(el => {
    el.editAsText().setBackgroundColor(null);
  });
}

function getAllTextElements(element) {
  const elements = [];
  
  const numChildren = element.getNumChildren ? element.getNumChildren() : 0;
  for (let i = 0; i < numChildren; i++) {
    const child = element.getChild(i);
    const type = child.getType();

    if (type === DocumentApp.ElementType.TEXT) {
      elements.push(child);
    } else {
      // Recurse into structural elements like Paragraph, Table, ListItem
      elements.push(...getAllTextElements(child));
    }
  }
  
  return elements;
}

function highlightSentence(body, sentence, color) {
  const range = body.findText(sentence);
  if (!range) return;

  const element = range.getElement();
  if (!element.editAsText) return;

  const text = element.editAsText();
  const start = range.getStartOffset();
  const end = range.getEndOffsetInclusive();

  // Check the background of the very first character of this match
  const existingColor = text.getBackgroundColor(start);

  // Determine whether to highlight full or half
  const length = end - start + 1;
  const halfEnd = start + Math.floor(length / 2);

  if (existingColor === null || existingColor === "") {
    // No highlight yet → highlight the entire match
    text.setBackgroundColor(start, end, color);
  } else {
    // Already highlighted → highlight only the first half
    text.setBackgroundColor(start, halfEnd, color);
  }
}


function getNextColor() {
  const props = PropertiesService.getScriptProperties();
  let hue = Number(props.getProperty('hue')) || 0;
  Logger.log(hue)

  // Next hue (increment by 20 degrees for good spacing)
  hue = (hue + 20) % 360;

  // Store back
  props.setProperty('hue', hue.toString());

  // Convert HSL to hex
  return hslToHex(hue, 80, 70);  // bright pastel-ish colors
}

function hslToHex(h, s, l) {
  s /= 100;
  l /= 100;

  const k = n => (n + h / 30) % 12;
  const a = s * Math.min(l, 1 - l);
  const f = n =>
    l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));

  const r = Math.round(255 * f(0));
  const g = Math.round(255 * f(8));
  const b = Math.round(255 * f(4));

  return "#" + [r, g, b].map(x =>
    x.toString(16).padStart(2, "0")
  ).join("");
}

function showSidebarNew() {
  const html = HtmlService.createHtmlOutputFromFile('sidebar-new')
    .setTitle('Story Map')
    .setWidth(600);
  DocumentApp.getUi().showSidebar(html);
}

function showSidebarPrevious() {
  const html = HtmlService.createHtmlOutputFromFile('sidebar-previous')
    .setTitle('Last Story Map')
    .setWidth(600);
  DocumentApp.getUi().showSidebar(html);
}

function loadLastMap() {
  const folder = getStoryMapFolder();
  const files = folder.getFiles();

  if (!files.hasNext()) {
    return { error: '⚠️ No story maps found in the "Story Maps" folder yet.' };
  }

  // Find most recently updated file
  let latestFile = files.next();
  while (files.hasNext()) {
    const f = files.next();
    if (f.getLastUpdated() > latestFile.getLastUpdated()) {
      latestFile = f;
    }
  }

  const blob = latestFile.getBlob();
  blob.setContentType('image/png');
  const base64 = Utilities.base64Encode(blob.getBytes());
  const dataUrl = `data:image/png;base64,${base64}`;

  return {
    dataUrl: dataUrl,
    fileName: latestFile.getName(),
    folderUrl: folder.getUrl(),
    lastUpdated: latestFile.getLastUpdated().toISOString()
  };
}


// TO DO
// 1. add a button underneath called 'save map' that saves the map to drive. I don't want every map to be automaticaly saved. maybe it's fine that it is
// 2. implement show last map - chat's current implementation is not working like it just saying "loading..." but doesn't do anything and I wouldn't want it to spend time loading anyway, the image should just be there

// need to implement it to maybe randomly poll every so often
// should make it so that even when the user clicks generate map it only updates using the information that has changed instead of running the entire document through the pipeline again


