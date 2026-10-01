// Code node "Keep due" (run once for all items). Sweeper branch.
// The queue rows are removed by now; continue with the patients who get a PDF.
return $('Due patients').all().filter((i) => !i.json.discard).map((i) => ({ json: i.json }));
