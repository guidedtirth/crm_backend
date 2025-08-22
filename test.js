const axios = require('axios');
const cheerio = require('cheerio');
const path = require('path');

// Configuration Constants
const TEST_MODE = false; // Set to false to fetch all projects
const TEST_ROWS = 5; // Number of rows to test initially
const MIN_DELAY = 3000; // 3 seconds minimum
const MAX_DELAY = 8000; // 8 seconds maximum
const MAX_PAGES_TO_SCRAPE = 2;

function getRandomDelay() {
    return Math.floor(Math.random() * (MAX_DELAY - MIN_DELAY + 1)) + MIN_DELAY;
}


async function fetchPageData(pageUrl) {
    try {
        const actualUrl = pageUrl.replace('view-source:', '');
        console.log("Fetching page data from:", actualUrl);

        const response = await axios.get(actualUrl, {
            headers: {
                'User-Agent':
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            },
        });

        const $ = cheerio.load(response.data);

        // --- Promoter Name & ID ---
        const projectNameText = $('#ctl00_ContentPlaceHolder1_lblProjectNameHeading').text().trim();
        const projectIdText = $('#ctl00_ContentPlaceHolder1_lblProjectNameWithID').text().trim();
        const ragistrationdateText = $('#ctl00_ContentPlaceHolder1_lblregisdate').text().trim();
        const promoterNameText = $('#ctl00_ContentPlaceHolder1_lblPromoterNameHeading').text().trim();
        const promoterIdText = $('#ctl00_ContentPlaceHolder1_lblPromoterNameWithID').text().trim();

        const projectName = projectNameText.replace(/^Project Name:\s*/, '');
        const projectId = projectIdText.replace(/^Project Id:\s*|\(|\)/g, '');
        const ragistrationdate = ragistrationdateText.replace(/^Registration Date:\s*/, '');
        const promoterName = promoterNameText.replace(/^Promoter Name:\s*/, '');
        const promoterId = promoterIdText.replace(/^Promoter Id:\s*|\(|\)/g, '');

        // --- Basic Details ---
        let basicDetails = {};

        $('#ctl00_ContentPlaceHolder1_PanelBasicDetails tr').each((i, row) => {
            const cells = $(row).find('td');

            for (let j = 0; j < cells.length; j += 2) {
                let key = $(cells[j]).text().trim().replace(/\s+/g, ' ').replace(/:$/, '');
                let valueElement = $(cells[j + 1]);
                let value = '';

                if (!key) continue;

                if (valueElement.find('select').length > 0) {
                    let selectedOption = valueElement.find('select option[selected]');
                    if (selectedOption.length === 0) {
                        selectedOption = valueElement.find('select option').filter((i, opt) => $(opt).text().trim() !== '');
                    }
                    value = $(selectedOption[0]).text().trim();
                }
                else if (valueElement.find('input').length > 0) {
                    value = valueElement.find('input').val()?.trim() || '';
                }
                else {
                    value = valueElement.text().trim().replace(/\s+/g, ' ');
                }

                if (value) {
                    basicDetails[key] = value;
                }
            }
        });

        // --- Only Latitude and Longtitude ---
        let geographicLocation = {};
        if ("Latitude" in basicDetails && "Longtitude" in basicDetails) {
            geographicLocation = {
                latitude: basicDetails["Latitude"],
                longitude: basicDetails["Longtitude"]
            };
        }

        // --- Other Details ---
        let otherDetails = {};
        $('#ctl00_ContentPlaceHolder1_Panel_OtherDetails tr').each((_, row) => {
            const cells = $(row).find('td');

            for (let i = 0; i < cells.length; i += 2) {
                let key = $(cells[i]).text().trim().replace(/\s+/g, ' ').replace(/:$/, '');
                let valueElement = $(cells[i + 1]);
                let value = '';

                if (!key) continue;

                // If cell contains input
                if (valueElement.find('input').length > 0) {
                    value = valueElement.find('input').val()?.trim() || '';
                }
                // If cell contains textarea
                else if (valueElement.find('textarea').length > 0) {
                    value = valueElement.find('textarea').val()?.trim() || '';
                }
                // Fallback to text
                else {
                    value = valueElement.text().trim().replace(/\s+/g, ' ');
                }

                if (value) {
                    otherDetails[key] = value;
                }
            }
        });

        // --- Development Works (Brief Description) ---
        let developmentWorks = {};
        $('#ctl00_ContentPlaceHolder1_Panel_DevelopmentWorks table tr').each((_, row) => {
            const cols = $(row).find('td');
            if (cols.length === 2) {
                let workName = $(cols[0]).text().trim().replace(/\s+/g, ' ');
                let valueElement = $(cols[1]);
                let workDetail = '';

                // If cell contains textarea, get .val()
                if (valueElement.find('textarea').length > 0) {
                    workDetail = valueElement.find('textarea').val()?.trim() || '';
                } else {
                    workDetail = valueElement.text().trim().replace(/\s+/g, ' ');
                }

                if (workName) {
                    developmentWorks[workName] = workDetail;
                }
            }
        });


        // --- Project Bank Details ---
        let projectBankDetails = {};
        $('#ctl00_ContentPlaceHolder1_Panel_BankDetails table tr').each((_, row) => {
            const cols = $(row).find('td');
            if (cols.length >= 2) {
                let key1 = $(cols[0]).text().trim().replace(/\s+/g, ' ').replace(/\*$/, '').trim();
                let value1 = '';
                let el1 = $(cols[1]);
                if (el1.find('input').length > 0) {
                    value1 = el1.find('input').val()?.trim() || '';
                } else if (el1.find('textarea').length > 0) {
                    value1 = el1.find('textarea').val()?.trim() || '';
                } else {
                    value1 = el1.text().trim();
                }
                if (key1) {
                    projectBankDetails[key1] = value1;
                }

                if (cols.length >= 4) {
                    let key2 = $(cols[2]).text().trim().replace(/\s+/g, ' ').replace(/\*$/, '').trim();
                    let value2 = '';
                    let el2 = $(cols[3]);
                    if (el2.find('input').length > 0) {
                        value2 = el2.find('input').val()?.trim() || '';
                    } else if (el2.find('textarea').length > 0) {
                        value2 = el2.find('textarea').val()?.trim() || '';
                    } else {
                        value2 = el2.text().trim();
                    }
                    if (key2) {
                        projectBankDetails[key2] = value2;
                    }
                }
            }
        });

        // --- Land Details ---

        let landDetails = {};
        landDetails["Plot Type"] = $("#ctl00_ContentPlaceHolder1_grdKhasra_ctl03_lblplotType").text().trim();
        landDetails["Khasra/Plot No"] = $("#ctl00_ContentPlaceHolder1_grdKhasra_ctl03_lblKhasraNo").text().trim();
        landDetails["Area(In Sq. Mt.)"] = $("#ctl00_ContentPlaceHolder1_grdKhasra_ctl03_lblArea").text().trim();


        landDetails["document Type"] = $("#ctl00_ContentPlaceHolder1_grdLadDetail_doc_ctl02_lbldoctype").text().trim();
        landDetails["Uploaded File"] = `https://up-rera.in/ViewDocument?Param=${$("#ctl00_ContentPlaceHolder1_grdLadDetail_doc_ctl02_lnkFileUploadLandDetails").text().trim()}`;
        landDetails["No."] = $("#ctl00_ContentPlaceHolder1_grdLadDetail_doc_ctl02_lblflg1").text().trim();
        landDetails["Date"] = $("#ctl00_ContentPlaceHolder1_grdLadDetail_doc_ctl02_lblDate1").text().trim();
        // --- Documents Uploaded ---
        let documents = [];

        $("#ctl00_ContentPlaceHolder1_grvdocumentdetails tr").each((i, row) => {
            if (i === 0) return; // skip header row
            let cols = $(row).find("td");

            if (cols.length > 0) {
                let doc = {
                    sno: $(cols[0]).text().trim(),
                    documentName: $(cols[1]).text().trim(),
                    uploadedFileName: $(cols[2]).text().trim(),
                    uploadedDate: $(cols[3]).text().trim(),
                    uploadDocType: $(cols[4]).text().trim(),
                    downloadLink: `https://up-rera.in/ViewDocument?Param=${$(cols[2]).text().trim()}`
                };
                documents.push(doc);
            }
        });

        // ---- Final object ----
        const result = {
            projectName,
            projectId,
            ragistrationdate,
            promoterName,
            promoterId,
            basicDetails,
            geographicLocation,
            otherDetails,
            "Development Works (Brief Description)": developmentWorks,
            "Project Bank Details": projectBankDetails,
            "Land Details": JSON.stringify(landDetails),
            "Documents uploaded": documents
        };

        return result;
    } catch (error) {
        console.error(error);
    }
}

async function scrapeProjectList(maxPages = MAX_PAGES_TO_SCRAPE) {
    let projectIds = [];
    let currentPage = 1;
    let hasNextPage = true;
    const baseUrl = 'https://up-rera.in/projects';
    let testMode = TEST_MODE;

    while (currentPage <= maxPages && hasNextPage) {
        try {
            console.log(`Fetching page ${currentPage}...`);

            const response = await axios.get(baseUrl, {
                params: { page: currentPage },
                headers: {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
                },
                timeout: 30000
            });

            console.log(`Response status: ${response.status}`);

            const $ = cheerio.load(response.data);

            // Select the projects table
            const projectTable = $('#grdPojDetail');

            if (projectTable.length === 0) {
                console.log('No project table found on page.');
                break;
            }

            let rowCount = 0;
            projectTable.find('tr').each((i, row) => {
                // Skip header row
                if (i === 0) return;

                if (testMode && rowCount >= TEST_ROWS) return false;

                const cols = $(row).find('td');
                if (cols.length >= 4) { // We need at least 4 columns to get RERA number
                    const reraNoElement = $(cols[3]).find('span[id*="lblRegistrationNo"]');
                    const reraNo = reraNoElement.text().trim();

                    // Extract ID from RERA number (UPRERAPRJ13276 → 13276)
                    const idMatch = reraNo.match(/UPRERAPRJ(\d+)/i);
                    const id = idMatch ? idMatch[1] : null;

                    if (id && !isNaN(id)) {
                        projectIds.push(id);
                        rowCount++;
                        console.log(`Found project ID: ${id} (RERA: ${reraNo})`);
                    } else {
                        console.log(`Skipping malformed RERA number: ${reraNo}`);
                    }
                }
            });

            if (testMode && rowCount === TEST_ROWS) {
                console.log(`Successfully fetched ${TEST_ROWS} test rows. Switching to full mode.`);
                testMode = false;
            }

            // Check for next page
            hasNextPage = $("a:contains('Next'), a[aria-label='Next']").not('.disabled').length > 0;
            currentPage++;

            await new Promise(resolve => setTimeout(resolve, getRandomDelay()));

        } catch (error) {
            console.error(`Error scraping page ${currentPage}:`, error.message);
            hasNextPage = false;
        }
    }

    return [...new Set(projectIds)];
}

// Utility function to split into chunks
function chunkArray(array, size) {
    const result = [];
    for (let i = 0; i < array.length; i += size) {
        result.push(array.slice(i, i + size));
    }
    return result;
}

// Main runner with batch processing
(async () => {
    try {
        console.log("Starting scraping process...");
        const ids = await scrapeProjectList();

        if (ids.length === 0) {
            console.log("No project IDs found.");
            return;
        }

        console.log(`Found ${ids.length} project IDs. Starting data collection in batches of 10...`);

        const fs = require('fs');
        const outputDir = path.join(__dirname, 'rera-up');
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }


        let results = [];
        let failedIds = [];

        // Split into batches of 10
        const batches = chunkArray(ids, 10);

        for (let b = 0; b < batches.length; b++) {
            const batch = batches[b];
            console.log(`\n🚀 Processing batch ${b + 1}/${batches.length} (size: ${batch.length})`);
            let filename = path.join(outputDir, `up-rera-results-${b + 1}.json`);

            // 🔑 Reset batch results for this file
            let batchResults = [];

            for (let i = 0; i < batch.length; i++) {
                const id = batch[i];
                try {
                    const url = `https://up-rera.in/Frm_View_Project_Details.aspx?id=${id}`;
                    console.log(`[Batch ${b + 1}] [${i + 1}/${batch.length}] Fetching data for project ID: ${id}`);

                    const data = await fetchPageData(url);

                    if (data) {
                        batchResults.push({ id, data });  // ✅ store only in this batch
                        results.push({ id, data });       // ✅ still keep global results
                        console.log(`✅ Successfully fetched data for project ${id}`);
                    } else {
                        failedIds.push(id);
                        console.log(`❌ Empty data for project ${id}`);
                    }

                    await new Promise(resolve => setTimeout(resolve, getRandomDelay()));
                } catch (error) {
                    failedIds.push(id);
                    console.error(`Error processing project ${id}:`, error.message);
                }
            }

            // ✅ Save only this batch’s 10 results
            fs.writeFileSync(filename, JSON.stringify(batchResults, null, 2));
            console.log(`💾 Batch ${b + 1} results saved to ${filename}`);
        }


        console.log("\n🎉 Scraping completed.");
        console.log(`✅ Successful fetches: ${results.length}`);
        console.log(`❌ Failed fetches: ${failedIds.length}`);
        if (failedIds.length > 0) {
            console.log("Failed IDs:", failedIds);
        }

    } catch (mainError) {
        console.error("Fatal error in main process:", mainError.message);
    } finally {
        console.log("Process completed.");
    }
})();