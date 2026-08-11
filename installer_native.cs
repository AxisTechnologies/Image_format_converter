using System;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Threading;
using System.Windows.Forms;
using System.Drawing;
using System.Diagnostics;

namespace PNG2JPEGConverterInstaller
{
    static class Program
    {
        private const string DownloadUrl = "https://github.com/AxisTechnologies/Image_format_converter/releases/latest/download/PNG2JPEGConverter_v1.0_Windows_Setup.zip";
        private const string AppName = "PNG -> JPEG Auto-Converter";
        private const string InstallDirName = "PNG2JPEGConverter";

        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InstallerForm());
        }

        public class InstallerForm : Form
        {
            private Label lblStatus;
            private ProgressBar progressBar;
            private Button btnInstall;
            private string installDir;
            private string tempZipPath;

            public InstallerForm()
            {
                this.Text = "Setup - PNG -> JPEG Auto-Converter";
                this.Size = new Size(480, 240);
                this.FormBorderStyle = FormBorderStyle.FixedDialog;
                this.MaximizeBox = false;
                this.MinimizeBox = false;
                this.StartPosition = FormStartPosition.CenterScreen;
                this.BackColor = Color.FromArgb(15, 23, 42);

                string appData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                installDir = Path.Combine(appData, InstallDirName);
                tempZipPath = Path.Combine(Path.GetTempPath(), "png2jpeg_setup.zip");

                InitializeComponents();
            }

            private void InitializeComponents()
            {
                Label lblTitle = new Label();
                lblTitle.Text = "📦 Setup - PNG -> JPEG Auto-Converter";
                lblTitle.Font = new Font("Segoe UI", 12, FontStyle.Bold);
                lblTitle.ForeColor = Color.FromArgb(248, 250, 252);
                lblTitle.Location = new Point(20, 20);
                lblTitle.AutoSize = true;
                this.Controls.Add(lblTitle);

                lblStatus = new Label();
                lblStatus.Text = "Click 'Install' to download & setup the application automatically.";
                lblStatus.Font = new Font("Segoe UI", 9, FontStyle.Regular);
                lblStatus.ForeColor = Color.FromArgb(148, 163, 184);
                lblStatus.Location = new Point(22, 50);
                lblStatus.Size = new Size(420, 30);
                this.Controls.Add(lblStatus);

                progressBar = new ProgressBar();
                progressBar.Location = new Point(24, 90);
                progressBar.Size = new Size(415, 16);
                this.Controls.Add(progressBar);

                btnInstall = new Button();
                btnInstall.Text = "Install Application";
                btnInstall.Font = new Font("Segoe UI", 10, FontStyle.Bold);
                btnInstall.ForeColor = Color.White;
                btnInstall.BackColor = Color.FromArgb(79, 70, 229);
                btnInstall.FlatStyle = FlatStyle.Flat;
                btnInstall.FlatAppearance.BorderSize = 0;
                btnInstall.Location = new Point(140, 130);
                btnInstall.Size = new Size(180, 38);
                btnInstall.Cursor = Cursors.Hand;
                btnInstall.Click += BtnInstall_Click;
                this.Controls.Add(btnInstall);
            }

            private void BtnInstall_Click(object sender, EventArgs e)
            {
                btnInstall.Enabled = false;
                Thread installThread = new Thread(StartProcess);
                installThread.IsBackground = true;
                installThread.Start();
            }

            private void UpdateStatus(string status, int percent)
            {
                if (this.InvokeRequired)
                {
                    this.Invoke(new Action(() => UpdateStatus(status, percent)));
                    return;
                }
                lblStatus.Text = status;
                if (percent >= 0 && percent <= 100)
                {
                    progressBar.Value = percent;
                }
            }

            private void StartProcess()
            {
                try
                {
                    // Priority 1: Check local release zip adjacent to installer executable or in dist
                    string exeDir = AppDomain.CurrentDomain.BaseDirectory;
                    string localZip = Path.Combine(exeDir, "PNG2JPEGConverter_v1.0_Windows_Setup.zip");
                    string distZip = Path.Combine(exeDir, "dist", "PNG2JPEGConverter_v1.0_Windows_Setup.zip");
                    string targetZip = tempZipPath;

                    if (File.Exists(localZip))
                    {
                        UpdateStatus("Installing from local package...", 50);
                        targetZip = localZip;
                    }
                    else if (File.Exists(distZip))
                    {
                        UpdateStatus("Installing from local dist package...", 50);
                        targetZip = distZip;
                    }
                    else
                    {
                        UpdateStatus("Downloading application package from GitHub...", 10);
                        try
                        {
                            using (WebClient wc = new WebClient())
                            {
                                wc.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)");
                                wc.DownloadProgressChanged += (s, ev) =>
                                {
                                    int pct = 10 + (int)(ev.ProgressPercentage * 0.6);
                                    UpdateStatus(String.Format("Downloading... {0}MB / {1}MB", ev.BytesReceived / (1024 * 1024), ev.TotalBytesToReceive / (1024 * 1024)), pct);
                                };
                                wc.DownloadFileTaskAsync(new Uri(DownloadUrl), targetZip).Wait();
                            }
                        }
                        catch (Exception dlEx)
                        {
                            Exception inner = dlEx.InnerException ?? dlEx;
                            throw new Exception("Could not download package from GitHub:\n" + inner.Message + "\n\nNote: Please publish the GitHub Release 'v1.0' on your GitHub repository, or keep 'PNG2JPEGConverter_v1.0_Windows_Setup.zip' in the same folder as this setup installer.");
                        }
                    }

                    // Terminate active instances before extracting updates
                    try
                    {
                        foreach (Process proc in Process.GetProcessesByName("PNG2JPEGConverter"))
                        {
                            proc.Kill();
                            proc.WaitForExit(1000);
                        }
                    }
                    catch { }

                    UpdateStatus("Extracting files...", 80);
                    if (!Directory.Exists(installDir))
                    {
                        Directory.CreateDirectory(installDir);
                    }

                    // Extract and overwrite files cleanly
                    using (ZipArchive archive = ZipFile.OpenRead(targetZip))
                    {
                        foreach (ZipArchiveEntry entry in archive.Entries)
                        {
                            string destinationPath = Path.Combine(installDir, entry.FullName);
                            if (string.IsNullOrEmpty(entry.Name))
                            {
                                Directory.CreateDirectory(destinationPath);
                            }
                            else
                            {
                                string parentDir = Path.GetDirectoryName(destinationPath);
                                if (!Directory.Exists(parentDir))
                                {
                                    Directory.CreateDirectory(parentDir);
                                }
                                entry.ExtractToFile(destinationPath, true);
                            }
                        }
                    }

                    UpdateStatus("Creating Desktop shortcut...", 95);
                    string desktop = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
                    string shortcutPath = Path.Combine(desktop, "PNG2JPEG Auto-Converter.lnk");
                    string exeTarget = Path.Combine(installDir, "PNG2JPEGConverter.exe");

                    string vbsScript = String.Format(
                        "Set WshShell = WScript.CreateObject(\"WScript.Shell\")\n" +
                        "Set shortcut = WshShell.CreateShortcut(\"{0}\")\n" +
                        "shortcut.TargetPath = \"{1}\"\n" +
                        "shortcut.WorkingDirectory = \"{2}\"\n" +
                        "shortcut.Description = \"PNG -> JPEG Auto Converter\"\n" +
                        "shortcut.Save",
                        shortcutPath, exeTarget, installDir
                    );

                    string vbsFile = Path.Combine(Path.GetTempPath(), "create_shortcut.vbs");
                    File.WriteAllText(vbsFile, vbsScript);

                    ProcessStartInfo psi = new ProcessStartInfo("cscript", "//Nologo \"" + vbsFile + "\"");
                    psi.CreateNoWindow = true;
                    psi.UseShellExecute = false;
                    Process p = Process.Start(psi);
                    p.WaitForExit();

                    UpdateStatus("✅ Installation Complete!", 100);

                    this.Invoke(new Action(() =>
                    {
                        DialogResult res = MessageBox.Show(String.Format("Installation complete!\n\nA Desktop shortcut has been created.\n\nWould you like to run the application now?"), "Setup Complete", MessageBoxButtons.YesNo, MessageBoxIcon.Information);
                        if (res == DialogResult.Yes)
                        {
                            Process.Start(new ProcessStartInfo(exeTarget) { WorkingDirectory = installDir });
                        }
                        this.Close();
                    }));
                }
                catch (Exception ex)
                {
                    this.Invoke(new Action(() =>
                    {
                        MessageBox.Show(String.Format("Installation failed:\n{0}", ex.Message), "Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        btnInstall.Enabled = true;
                    }));
                }
            }
        }
    }
}
