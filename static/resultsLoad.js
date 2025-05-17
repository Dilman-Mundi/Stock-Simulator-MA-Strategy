document.addEventListener("DOMContentLoaded", function() {
   document.getElementById("calculate-btn").addEventListener("click", function() {

      document.getElementById("results").style.display = "none";
      document.getElementById("results").innerHTML = "";
      this.value = "verifying input...";
      this.setAttribute("aria-busy", "true");

      const fields = {
        ticker: document.getElementById("ticker").value.trim(),
        fsma: document.getElementById("fsma").value.trim(),
        ssma: document.getElementById("ssma").value.trim(),
        transaction_fee: document.getElementById("transaction_fee").value.trim(),
        start_date: document.getElementById("start_date").value.trim(),
        end_date: document.getElementById("end_date").value.trim(),
        money: document.getElementById("money").value.trim()
      }

      const params = new URLSearchParams({
         ticker: fields.ticker,
         fsma: fields.fsma,
         ssma: fields.ssma,
         transaction_fee: fields.transaction_fee,
         start_date: fields.start_date,
         end_date: fields.end_date,
         money: fields.money
       });
       
       fetch("/verifyInput", {
         method: "POST",
         body: params
       })
      .then(response => {
        if (!response.ok) throw new Error(`VerifyInput failed: ${response.status} ${response.statusText}`);
        return response.json();
      })
      .then(data => {
        const validity = data.valid;
        const error = data.errors;
        const fieldKeys = Object.keys(fields);

        for (let i = 0; i < fieldKeys.length; i++) {
          const field = document.getElementById(fieldKeys[i]);
          if (validity[i] == true) {
            field.removeAttribute("aria-invalid");
            document.getElementById(fieldKeys[i]+"-error").textContent = ""
          }
          else {
            field.setAttribute("aria-invalid", "true");
            document.getElementById(fieldKeys[i]+"-error").textContent = error[i]
          }
        }
        if (!data.success) {
          this.value = "Calculate"
          this.removeAttribute("aria-busy");
        }
        if (data.success) {
          this.value = "running simulation..."
          const values = data.form_values;
          const payload = new URLSearchParams ({
            ticker: values[0],
            fSMA: values[1],
            sSMA: values[2],
            transaction_fee: values[3],
            start_date: values[4],
            end_date: values[5],
            money: values[6],
            fullStockNames: JSON.stringify(values[7])
          });

          fetch("/runSimulation", {
            method: "POST",
            body: payload
          })
          .then(response => {
            if (!response.ok) throw new Error(`runSimulation failed: ${response.status} ${response.statusText}`);
            return response.json();
          })
          .then(simulationValues => {
            this.value = "loading results ..."

            window.simulationResults = {
              fullStockNames: JSON.stringify(values[7]),
              df: JSON.stringify(simulationValues.df),
              tickers: values[0],
              fsma: values[1],
              ssma: values[2]
            };

            fetch("/loadResults")
            .then(response => {
              if (!response.ok) throw new Error(`loadResults failed: ${response.status} ${response.statusText}`);
              return response.text();
            })
            .then(html => {
              document.getElementById("results").innerHTML = html;
              const tableParams = {
                fullStockNames: JSON.stringify(values[7]),
                transactions: JSON.stringify(simulationValues.transactions),
                pL: JSON.stringify(simulationValues.pL),
                ret: JSON.stringify(simulationValues.ret),
                plotDates: JSON.stringify(simulationValues.plotDates),
                plotNetWorth: JSON.stringify(simulationValues.plotNetWorth)
              }
              Promise.all([
                fetch("/getTableValues", {
                  method: "POST",
                  body: new URLSearchParams(tableParams)
                }).then(res => {
                  if (res.status === 413) throw new Error("413 Payload Too Large on /getTableValues");
                  if (!res.ok) throw new Error(`Error ${res.status} from /getTableValues`);
                  return res.json();
                }),
                fetch("/plot", {
                  method: "POST",
                  body: new URLSearchParams(tableParams)
                }).then(res => {
                  if (res.status === 413) throw new Error("413 Payload Too Large on /plot");
                  if (!res.ok) throw new Error(`Error ${res.status} from /plot`);
                  return res.json();
                }),
              ])
              .then(([tableValues, plotData]) => {
                // table
                const tbody = document.getElementById("table-body");
                tbody.innerHTML = "";
              
                const previewRows = tableValues.slice(0, tableValues.length);
                previewRows.forEach((row, index) => {
                  const tr = document.createElement("tr");

                  const plColor = parseFloat(row.PL) > 0 ? "#25a48e" : parseFloat(row.PL) < 0 ? "#e03b4e" : "inherit";
                  const retColor = parseFloat(row.ret) > 0 ? "#25a48e" : parseFloat(row.ret) < 0 ? "#e03b4e" : "inherit";

                  tr.innerHTML = `
                    <th scope="row">${index + 1}</th>
                    <td>${row.stockName}</td>
                    <td>${Number(row.transactions).toLocaleString()}</td>
                    <td style="color: ${plColor}">${"$"+String(Number(row.PL).toLocaleString())}</td>
                    <td style="color: ${retColor}">${String(Number(row.ret).toLocaleString()+"%/yr")}</td>
                  `;
                  tbody.appendChild(tr);
                });
                // plotData
                const colors = ["blue", "red", "green", "purple", "yellow"];
                const traces = plotData.map((stock, i) => ({
                  x: stock.x,
                  y: stock.y,
                  mode: "lines",
                  hoverinfo: "text",
                  text: stock.hover.map(entry => {
                      return entry.replace(/(\d{4}-\d{2}-\d{2})\s.*(\$[\d,.]+)/, '$1<br>Net Worth: $2');
                  }),
                  name: stock.name,
                  line: { color: colors[i % colors.length] }
                }));

                const layout = {
                  title: "Net Worth Over Time",
                  autosize: true,
                  width: window.innerWidth * 0.9,
                  xaxis: {
                    title: "Date",
                    tickformat: "%Y",
                    type: "date"
                  },
                  yaxis: { title: "Net Worth" },
                  showlegend: true, // Ensures legend is displayed
                  legend: { 
                      orientation: "v", // Vertical legend
                      x: 1,  // Places legend on the right side
                      y: 0.5 // Centers legend vertically
                  }
                };

                Plotly.newPlot("plot-container", traces, layout);

                this.value = "Calculate"
                this.removeAttribute("aria-busy");

                const scrollPosition = window.pageYOffset || document.documentElement.scrollTop;
                document.getElementById("results").style.display = "block";
                window.scrollTo(0, scrollPosition);
                setTimeout(() => {
                  document.getElementById("results").scrollIntoView({ behavior: "smooth", block: "start" });
                }, 200);
              })
              .catch(error => {
                console.error("Error during data fetch:", error);
                alert(error.message); // Show user-friendly error
                this.value = "Calculate";
                this.removeAttribute("aria-busy");
              });
            })
          })
        }
      });
   });
  document.getElementById("results").addEventListener("click", function(event) {
    if (event.target && event.target.id === "download-btn") {
      const results = window.simulationResults;

      const formData = new URLSearchParams({
        fullStockNames: results.fullStockNames,
        df_json: results.df
      });

      fetch("/download_excel", {
        method: "POST",
        body: formData
      })
        .then(response => {
          if (!response.ok) throw new Error(`Download failed: ${response.status} ${response.statusText}`);
          const disposition = response.headers.get("Content-Disposition");
          const filename = disposition.split("filename=")[1].replace(/['"]/g, "").trim();
          return response.blob().then(blob => ({ blob, filename }));
        })
        .then(({ blob, filename }) => {
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = filename;
          document.body.appendChild(a);
          a.click();
          a.remove();
          window.URL.revokeObjectURL(url);
        });
    }
  });
});