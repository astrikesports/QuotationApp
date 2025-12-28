import tkinter as tk
from tkinter import ttk, messagebox, Listbox, simpledialog
import os, json
from datetime import datetime
import pandas as pd

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import Image, PageBreak, KeepTogether, KeepInFrame

from tkinter import filedialog



# ================= SKU DB =================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Y5VQsIQ33UYPOe1-Ul6VV7vv79lbrHnu8aRoAgYLeho/export?format=csv"
STOCK_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Uef9a1MZHI9JshrkPJBeezI9HPdZ4ElI0vgknj-Bys0/export?format=csv"


def safe_int(val):
    try:
        if pd.isna(val):
            return 0
        return int(float(val))
    except:
        return 0


def load_sku_db():
    global SKU_DB
    try:
        df = pd.read_csv(SHEET_URL)
        df.columns = df.columns.str.strip().str.upper()   # 🔥 FIX
        print("COLUMNS:", df.columns.tolist())
    except Exception as e:
        print("LOAD FAILED:", e)
        return

    SKU_DB = {
        str(r["SKU"]).upper(): {
            "MRP": float(r["MRP"]) if not pd.isna(r["MRP"]) else 0,
            "PCS": safe_int(r.get("PCS", 0))   # 🔥 SAFE ACCESS
        }
        for _, r in df.iterrows()
    }

    print("PCS CHECK SAMPLE:", list(SKU_DB.items())[:3])
    print("SKU_DB UPDATED:", list(SKU_DB.keys())[:5])  # 👈 ADD


DOWNLOADS = os.path.join(os.path.expanduser("~"), "Downloads")
SIZES = ["S", "M", "L", "XL", "2XL", "3XL", "4XL"]


# ================= APP =================
class QuotationApp:
    
    def safe(self, txt):
        if not txt:
            return ""
        return (
            str(txt)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("%", "&#37;")
        )
    
    def refresh_data(self):
        try:
            load_sku_db()   # 🔄 Reload Google Sheet

            messagebox.showinfo(
                "Refreshed",
                "SKU & Stock data refreshed successfully"
            )
        except Exception as e:
            messagebox.showerror(
                "Refresh Error",
                str(e)
            )

    
    def parse_sizes(self, size_text):
        size_map = {
            "S": "", "M": "", "L": "",
            "XL": "", "2XL": "", "3XL": "", "4XL": ""
        }

        if not size_text:
            return size_map

        for part in size_text.split(","):
            try:
                s, q = part.strip().split("-")
                if s in size_map:
                    size_map[s] = q
            except:
                pass

        return size_map

    def update_all_item_rates(self):
        if not self.items:
            messagebox.showinfo("Info", "No items to update")
            return

        rate_disc = self.rate_discount_var.get()
        if rate_disc not in (55, 57):
            messagebox.showerror("Error", "Select Rate Discount (55% or 57%)")
            return

        try:
            sp_disc = float(self.sp_discount.get())
        except:
            sp_disc = 0

        updated = 0

        for item in self.items:
            # ❌ Skip sample items
            if "(SAMPLE)" in item["desc"]:
                continue

            # ❌ Skip manual rate items
            if item.get("is_manual"):
                continue

            sku = item["desc"].replace(" (SAMPLE)", "").strip()

            if sku not in SKU_DB:
                continue

            mrp = SKU_DB[sku]["MRP"]

            # ---- APPLY RATE DISCOUNT ----
            raw_rate = (mrp * (100 - rate_disc)) / 100
            rate_after_radio = int(raw_rate) + (1 if raw_rate - int(raw_rate) >= 0.5 else 0)

            # ---- APPLY SP DISCOUNT ----
            if sp_disc > 0:
                raw_final = rate_after_radio - (rate_after_radio * sp_disc / 100)
                final_rate = int(raw_final) + (1 if raw_final - int(raw_final) >= 0.5 else 0)
            else:
                final_rate = rate_after_radio

            item["rate"] = final_rate
            item["amount"] = item["pcs"] * final_rate
            updated += 1

        self.refresh()

        messagebox.showinfo(
            "Rates Updated",
            f"{updated} item(s) rate updated successfully"
        )


    def __init__(self, root):
        self.root = root
        load_sku_db()
        self.root.title("Quotation Software")
        self.root.state("zoomed")
        self.payment_image_path = ""


        self.items = []
        self.selected_index = None

        self.build_ui()

    def update_payment_image_ui(self):
        if self.payment_image_path and os.path.exists(self.payment_image_path):
            self.pay_img_status.config(
                text="Payment Image: Selected",
                fg="green"
            )
            self.pay_img_remove_btn.config(state="normal")
        else:
            self.pay_img_status.config(
                text="Payment Image: Not Selected",
                fg="red"
            )
            self.pay_img_remove_btn.config(state="disabled")

    # ================= UI =================
    def build_ui(self):

        header = tk.Frame(self.root, bg="#2d3436", height=80)
        header.pack(fill="x")

        # ---------- LEFT SIDE (Company + Party + Phone) ----------
        left_header = tk.Frame(header, bg="#2d3436")
        left_header.pack(side="left", padx=20, pady=6)

        tk.Label(
            left_header,
            text="ASTRIKE SPORTSWEAR PVT LTD",
            fg="white",
            bg="#2d3436",
            font=("Arial", 18, "bold")
        ).pack(anchor="w")

        self.party_header_lbl = tk.Label(
            left_header,
            text="Party : -",
            fg="#dfe6e9",
            bg="#2d3436",
            font=("Arial", 11)
        )
        self.party_header_lbl.pack(anchor="w", pady=(2, 0))

        self.phone_header_lbl = tk.Label(
            left_header,
            text="Phone : -",
            fg="#b2bec3",
            bg="#2d3436",
            font=("Arial", 10)
        )
        self.phone_header_lbl.pack(anchor="w")

        # ---------- RIGHT SIDE (BUTTON) ----------
        btn_frame = tk.Frame(header, bg="#2d3436")
        btn_frame.pack(side="right", padx=20)
        
        # ---- REFRESH BUTTON ----
        refresh_btn = tk.Button(
        btn_frame,
        text="🔄 Refresh",
        command=self.refresh_data,
        bg="#27ae60",
        fg="white",
        font=("Arial", 11, "bold"),
        relief="flat",
        padx=12,
        pady=6
    )
        refresh_btn.pack(side="left", padx=(0, 8))

        # ---- SAVE PDF ----
        save_btn = tk.Button(
            btn_frame,
            text="💾 Save PDF",
            command=self.save_pdf,
            bg="#6c5ce7",
            fg="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=12,
            pady=6
        )
        save_btn.pack(side="left", padx=(0, 8))

        # ---- LOAD OLD QUOTATION ----
        load_btn = tk.Button(
            btn_frame,
            text="📂 Load",
            command=self.load_old_data,
            bg="#636e72",
            fg="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=12,
            pady=6
        )
        load_btn.pack(side="left", padx=(0, 8))

        # ---- NEW QUOTATION ----
        new_btn = tk.Button(
            btn_frame,
            text="➕ New",
            command=self.new_quotation,
            bg="#0984e3",
            fg="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=12,
            pady=6
        )
        new_btn.pack(side="left", padx=(0, 8))

        # ---- UPDATE RATES ----
        update_btn = tk.Button(
            btn_frame,
            text="🔁 Update Rates",
            command=self.update_all_item_rates,
            bg="#00b894",
            fg="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=12,
            pady=6,

        )
        update_btn.pack(side="left")

        # Hover UX
        update_btn.bind("<Enter>", lambda e: update_btn.config(bg="#019875"))
        update_btn.bind("<Leave>", lambda e: update_btn.config(bg="#00b894"))
        save_btn.bind("<Enter>", lambda e: save_btn.config(bg="#6c5ce7"))
        save_btn.bind("<Leave>", lambda e: save_btn.config(bg="#5a4bd8"))
        load_btn.bind("<Enter>", lambda e: load_btn.config(bg="#636e72"))
        load_btn.bind("<Leave>", lambda e: load_btn.config(bg="#4d5656"))
        new_btn.bind("<Enter>", lambda e: new_btn.config(bg="#0984e3"))
        new_btn.bind("<Leave>", lambda e: new_btn.config(bg="#0873c4"))
        refresh_btn.bind("<Enter>", lambda e: refresh_btn.config(bg="#37d77a"))
        refresh_btn.bind("<Leave>", lambda e: refresh_btn.config(bg="#27ae60"))


        # ================= MAIN CONTAINER =================
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True)

        # ================= LEFT PANEL =================
        LEFT_WIDTH = 360   # ← left panel ki fixed width

        self.left = tk.Frame(
            main,
            bg="#f4f4f4",
            width=LEFT_WIDTH
        )
        self.left.pack(side="left", fill="y")
        self.left.pack_propagate(False)   # 🔥 left ko fixed rakhega

        # Canvas for scroll
        canvas = tk.Canvas(
            self.left,
            bg="#f4f4f4",
            width=LEFT_WIDTH,
            highlightthickness=0
        )
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(
            self.left,
            orient="vertical",
            command=canvas.yview
        )
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        # Inner scrollable frame
        self.left = tk.Frame(canvas, bg="#f4f4f4", padx=10, pady=10)

        canvas_window = canvas.create_window(
            (0, 0),
            window=self.left,
            anchor="nw"
        )

        # Auto resize scroll region
        def on_left_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.left.bind("<Configure>", on_left_configure)

        # Mouse wheel scroll
        canvas.bind_all(
            "<MouseWheel>",
            lambda e: canvas.yview_scroll(-1 * int(e.delta / 120), "units")
        )

        # ================= RIGHT PANEL =================
        self.right = tk.Frame(
            main,
            bg="white",
            padx=10,
            pady=10
        )
        self.right.pack(side="left", fill="both", expand=True)
        # ---------- PARTY ----------
        self.party = self.field("Party Name")
        self.address = self.field("Address")
        self.phone = self.field("Phone")
        self.sales_person = self.field("Sales Person")
        self.rate_discount_var = tk.IntVar()  # default 57%
        #self.discount = self.field("Discount %")
        
        tk.Label(self.left, text="Rate Discount (%)", bg="#f4f4f4",
         font=("Arial", 10, "bold")).pack(anchor="w", pady=(6, 2))

        disc_frame = tk.Frame(self.left, bg="#f4f4f4")
        disc_frame.pack(anchor="w")

        tk.Radiobutton(
            disc_frame,
            text="55%",
            variable=self.rate_discount_var,
            value=55,
            bg="#f4f4f4",
            command=self.refresh
        ).pack(side="left", padx=5)

        tk.Radiobutton(
            disc_frame,
            text="57%",
            variable=self.rate_discount_var,
            value=57,
            bg="#f4f4f4",
            command=self.refresh
        ).pack(side="left", padx=5)
        
        tk.Label(
            self.left,
            text="Sales Person Discount (%)",
            bg="#f4f4f4"
        ).pack(anchor="w")

        self.sp_discount = tk.Entry(self.left)
        self.sp_discount.pack(fill="x", pady=2)



        self.party.bind("<KeyRelease>", lambda e: self.update_header())
        self.phone.bind("<KeyRelease>", lambda e: self.update_header())
        
        tk.Button(
        self.left,
        text="📦 Check Stock",
        command=self.open_stock_checker
    ).pack(fill="x", pady=5)
        
        tk.Button(
        self.left,
        text="💳 Add Payment Image",
        command=self.select_payment_image
    ).pack(fill="x", pady=3)



        # ---------- ITEM ----------
        tk.Label(self.left, text="Item Details",
                 font=("Arial", 14, "bold"),
                 bg="#f4f4f4").pack(anchor="w", pady=8)

        self.desc = self.field("SKU")
        self.desc.bind("<KeyRelease>", self.on_sku_type)

        self.sku_listbox = Listbox(self.root, height=5)
        self.sku_listbox.bind("<<ListboxSelect>>", self.fill_sku)

        self.manual_price = tk.IntVar()
        tk.Checkbutton(self.left, text="Manual Price",
                       variable=self.manual_price,
                       bg="#f4f4f4").pack(anchor="w")

        self.rate = self.field("Rate")
        self.rate.config(state="disabled")
        self.manual_price.trace_add("write", lambda *a: self.toggle_rate())

        tk.Label(self.left, text="Size-wise Box Qty",
                 font=("Arial", 12, "bold"),
                 bg="#f4f4f4").pack(anchor="w", pady=(8,2))

        self.size_boxes = {}
        for s in SIZES:
            r = tk.Frame(self.left, bg="#f4f4f4")
            r.pack(anchor="w")
            tk.Label(r, text=s, width=5, bg="#f4f4f4").pack(side="left")
            e = tk.Entry(r, width=6)
            e.pack(side="left", padx=5)
            self.size_boxes[s] = e

        tk.Button(self.left, text="➕ Add Item", command=self.add_item).pack(fill="x", pady=3)

        # ---------- SAMPLE ----------
        tk.Label(self.left, text="Sample Item",
                 font=("Arial", 12, "bold"),
                 bg="#f4f4f4").pack(anchor="w", pady=(10,2))

        self.sample_pcs = self.field("Sample PCS")
        self.sample_rate = self.field("Sample Rate")

        tk.Button(self.left, text="🧪 Add Sample Item",
                  bg="#ffeaa7",
                  command=self.add_sample_item).pack(fill="x", pady=3)

        tk.Button(self.left, text="✏️ Update Selected", command=self.update_item).pack(fill="x", pady=3)
        tk.Button(self.left, text="❌ Delete Selected", command=self.delete_item).pack(fill="x", pady=3)

        # ---------- BILLING ----------
        self.shipping = self.field("Shipping")

        # ===== BILL DISCOUNT =====
        tk.Label(self.left, text="Bill Discount Type", bg="#f4f4f4").pack(anchor="w")

        self.bill_disc_type = tk.StringVar(value="AMOUNT")

        tk.Radiobutton(
            self.left, text="Rs Amount",
            variable=self.bill_disc_type,
            value="AMOUNT",
            bg="#f4f4f4"
        ).pack(anchor="w")

        tk.Radiobutton(
            self.left, text="Percentage (%)",
            variable=self.bill_disc_type,
            value="PERCENT",
            bg="#f4f4f4"
        ).pack(anchor="w")

        self.bill_discount = self.field("Bill Discount")

        # =========================
        self.advance = self.field("Advance")


        # ---- PAYMENT IMAGE STATUS ----
        pay_frame = tk.Frame(self.left, bg="#f4f4f4")
        pay_frame.pack(fill="x", pady=4)

        self.pay_img_status = tk.Label(
            pay_frame,
            text="Payment Image: Not Selected",
            bg="#f4f4f4",
            fg="red",
            anchor="w"
        )
        self.pay_img_status.pack(side="left", fill="x", expand=True)

        self.pay_img_remove_btn = tk.Button(
            pay_frame,
            text="❌",
            width=3,
            command=self.remove_payment_image
        )
        self.pay_img_remove_btn.pack(side="right")
        self.pay_img_remove_btn.config(state="disabled")


        # ---------- REMARK CARD ----------
        remark_frame = tk.Frame(
            self.left,
            bg="white",
            bd=1,
            relief="solid"
        )
        remark_frame.pack(fill="x", pady=10)

        tk.Label(
            remark_frame,
            text="REMARK",
            bg="white",
            fg="#2d3436",
            font=("Arial", 10, "bold")
        ).pack(anchor="w", padx=10, pady=(8, 4))

        ttk.Separator(
            remark_frame,
            orient="horizontal"
        ).pack(fill="x", padx=8, pady=4)

        self.remark = tk.Text(
            remark_frame,
            height=3,
            width=35,     # 👈 width characters me
            wrap="word",
            bd=1,
            relief="solid"
        )
        self.remark.pack(padx=15, pady=(0, 10))


        
        
        # ---------- TABLE ----------
        cols = ("desc", "size", "pcs", "rate", "amount")
        self.tree = ttk.Treeview(self.right, columns=cols, show="headings")
        for c in cols:
            self.tree.heading(c, text=c.upper())
            self.tree.column(c, anchor="center", width=140)
        self.tree.pack(fill="both", expand=True)

        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.right.bind("<Button-1>", self.clear_selection)

        # ---------- BOTTOM ----------
        bottom = tk.Frame(self.root, bg="#dfe6e9", height=45)
        bottom.pack(fill="x", side="bottom")

        self.summary = tk.Label(
            bottom,
            text="PCS: 0 | AMOUNT: Rs0 | NET: Rs0",
            font=("Arial", 12, "bold"), bg="#dfe6e9"
        )
        self.summary.pack(pady=8)

    # ================= HELPERS =================
    
    def select_payment_image(self):
        path = filedialog.askopenfilename(
        title="Select Payment Image",
        filetypes=[
            ("Image Files", "*.png *.jpg *.jpeg *.webp"),
            ("All Files", "*.*")
        ]
    )

        if path:
            self.payment_image_path = path
            self.update_payment_image_ui()
            messagebox.showinfo("Payment Image", "Payment image added successfully")
            
    def remove_payment_image(self):
            self.payment_image_path = ""
            self.update_payment_image_ui()

    
    def field(self, label):
        tk.Label(self.left, text=label, bg="#f4f4f4").pack(anchor="w")
        e = tk.Entry(self.left)
        e.pack(fill="x", pady=2)
        return e

    # ===== HEADER AUTO UPDATE =====
    def update_header(self):
        party = self.party.get().strip()
        phone = self.phone.get().strip()

        self.party_header_lbl.config(
            text=f"Party : {party}" if party else "Party : -"
        )
        self.phone_header_lbl.config(
            text=f"Phone : {phone}" if phone else "Phone : -"
        )

            # ===== NEW QUOTATION FUNCTION =====
    def new_quotation(self):
        if self.items:
            confirm = messagebox.askyesno(
                "New Quotation",
                "Current quotation will be cleared.\nDo you want to continue?"
            )
            if not confirm:
                return

        # ---- CLEAR ITEMS ----
        self.items = []
        self.tree.delete(*self.tree.get_children())

        # ---- CLEAR ENTRY FIELDS ----
        for field in [
            self.party, self.phone, self.address,
            self.sales_person, self.shipping,
            self.bill_discount, self.advance,
            self.sp_discount
        ]:
            field.delete(0, tk.END)

        # ---- RESET RATE DISCOUNT ----
        self.rate_discount_var.set(57)

        # ---- CLEAR SIZE BOXES ----
        for e in self.size_boxes.values():
            e.delete(0, tk.END)

        # ---- RESET PAYMENT IMAGE ----
        self.payment_image_path = ""
        self.update_payment_image_ui()

        # ---- RESET HEADER TEXT ----
        self.update_header()

        # ---- REFRESH TABLE & SUMMARY ----
        self.refresh()


    def load_stock_data(self):
        try:
            df = pd.read_csv(STOCK_SHEET_URL)
            df["SKU"] = df["SKU"].astype(str).str.upper()
            self.stock_db = {
                row["SKU"]: row["STOCK"]
                for _, row in df.iterrows()
            }
        except Exception as e:
            messagebox.showerror("Stock Error", f"Unable to load stock sheet\n{e}")
            self.stock_db = {}

    # ================= SKU AUTOSUGGEST =================
    def on_sku_type(self, e):
        typed = self.desc.get().upper()
        self.sku_listbox.delete(0, tk.END)

        if not typed:
            self.sku_listbox.place_forget()
            return

        for s in SKU_DB:
            if typed in s:
                self.sku_listbox.insert(tk.END, s)

        if self.sku_listbox.size() == 0:
            self.sku_listbox.place_forget()
            return

        x = self.desc.winfo_rootx()
        y = self.desc.winfo_rooty() + self.desc.winfo_height()
        self.sku_listbox.place(x=x, y=y, width=self.desc.winfo_width())

    def fill_sku(self, e):
        if not self.sku_listbox.curselection():
            return
        self.desc.delete(0, tk.END)
        self.desc.insert(0, self.sku_listbox.get(self.sku_listbox.curselection()))
        self.sku_listbox.place_forget()

    # ================= LOGIC =================
    def toggle_rate(self):
        self.rate.config(state="normal" if self.manual_price.get() else "disabled")

    def calc_rate_auto(self, sku):
        # ----- Level 1: Rate Discount (Radio) -----
        rate_disc = self.rate_discount_var.get()
        if rate_disc not in (55, 57):
            messagebox.showerror(
                "Discount Required",
                "Please select Rate Discount (55% or 57%)"
            )
            raise ValueError("Rate discount not selected")

        mrp = SKU_DB[sku]["MRP"]

        # MRP → Rate Discount
        raw_rate = (mrp * (100 - rate_disc)) / 100
        rate_after_radio = int(raw_rate) + (1 if raw_rate - int(raw_rate) >= 0.5 else 0)

        # ----- Level 2: Sales Person Discount -----
        try:
            sp_disc = float(self.sp_discount.get())
        except:
            sp_disc = 0

        if sp_disc > 0:
            raw_final = rate_after_radio - (rate_after_radio * sp_disc / 100)
            final_rate = int(raw_final) + (1 if raw_final - int(raw_final) >= 0.5 else 0)
        else:
            final_rate = rate_after_radio

        return final_rate



    def add_item(self):
        sku = self.desc.get().upper()
        if sku not in SKU_DB:
            messagebox.showerror("Error", "Valid SKU required")
            return

        boxes = 0
        sizes = []
        for s, e in self.size_boxes.items():
            if e.get():
                b = int(e.get())
                boxes += b
                sizes.append(f"{s}-{b}")

        if boxes == 0:
            messagebox.showerror("Error", "Enter size qty")
            return

        pcs = boxes * SKU_DB[sku]["PCS"]
        
        try:
            rate = int(self.rate.get()) if self.manual_price.get() else self.calc_rate_auto(sku)
        except:
            return

        

        self.items.append({
            "desc": sku,
            "size": ", ".join(sizes),
            "pcs": pcs,
            "rate": rate,
            "amount": pcs * rate,
            "is_manual": True if self.manual_price.get() else False
        })

        self.clear_item_form()
        self.refresh()

    def add_sample_item(self):
        try:
            pcs = int(self.sample_pcs.get())
            rate = int(self.sample_rate.get())
        except:
            messagebox.showerror("Error", "Sample PCS & Rate required")
            return

        desc = self.desc.get().strip() or "SAMPLE ITEM"

        self.items.append({
            "desc": f"{desc} (SMPL)",
            "size": "",
            "pcs": pcs,
            "rate": rate,
            "amount": pcs * rate,
            "is_manual": True
        })

        self.sample_pcs.delete(0, tk.END)
        self.sample_rate.delete(0, tk.END)
        self.refresh()


    def on_select(self, e):
        sel = self.tree.selection()
        if not sel:
            return

        self.selected_index = self.tree.index(sel[0])
        it = self.items[self.selected_index]

        self.desc.delete(0, tk.END)
        self.desc.insert(0, it["desc"].replace(" (SMPL)", ""))

        self.rate.config(state="normal")
        self.rate.delete(0, tk.END)
        self.rate.insert(0, it["rate"])

        for ent in self.size_boxes.values():
            ent.delete(0, tk.END)

        if it["size"]:
            for part in it["size"].split(","):
                s, q = part.strip().split("-")
                if s in self.size_boxes:
                    self.size_boxes[s].insert(0, q)

    def clear_item_form(self):
        self.desc.delete(0, tk.END)
        self.rate.delete(0, tk.END)
        for e in self.size_boxes.values():
            e.delete(0, tk.END)

    def clear_selection(self, event):
        self.tree.selection_remove(self.tree.selection())
        self.selected_index = None
        self.clear_item_form()

    def update_item(self):
        if self.selected_index is None:
            return
        self.items.pop(self.selected_index)
        self.selected_index = None
        self.add_item()

    def delete_item(self):
        if self.selected_index is not None:
            del self.items[self.selected_index]
            self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        total_pcs = total_amt = 0

        for i in self.items:
            self.tree.insert("", tk.END,
                values=(i["desc"], i["size"], i["pcs"], i["rate"], i["amount"]))
            total_pcs += i["pcs"]
            total_amt += i["amount"]

        shipping_raw = self.shipping.get().strip()
        ship = int(shipping_raw) if shipping_raw.isdigit() else 0
        adv = int(self.advance.get()) if self.advance.get().isdigit() else 0
        bill_disc_input = int(self.bill_discount.get()) if self.bill_discount.get().isdigit() else 0

        if self.bill_disc_type.get() == "PERCENT":
            bill_disc_amt = int((total_amt * bill_disc_input) / 100)
        else:
            bill_disc_amt = bill_disc_input

        net = total_amt + ship - bill_disc_amt - adv


        self.summary.config(
            text=f"PCS: {total_pcs} | AMOUNT: Rs{total_amt} | SHIPPING: {shipping_raw or '-'} | ADVANCE: Rs{adv} | NET: Rs{net}"
        )


    def open_stock_checker(self):
        # Load stock fresh every time
        self.load_stock_data()

        win = tk.Toplevel(self.root)
        win.title("Check Stock")
        win.geometry("400x450")
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="Search SKU", font=("Arial", 12, "bold")).pack(pady=5)

        search_var = tk.StringVar()
        search_entry = tk.Entry(win, textvariable=search_var)
        search_entry.pack(fill="x", padx=10)

        listbox = tk.Listbox(win, height=10)
        listbox.pack(fill="both", expand=True, padx=10, pady=5)

        result_lbl = tk.Label(win, text="", font=("Arial", 11, "bold"))
        result_lbl.pack(pady=10)

        def on_type(*args):
            typed = search_var.get().upper()
            listbox.delete(0, tk.END)

            if not typed:
                return

            for sku in self.stock_db:
                if typed in sku:
                    listbox.insert(tk.END, sku)

        def on_select(evt):
            if not listbox.curselection():
                return
            sku = listbox.get(listbox.curselection())
            stock = self.stock_db.get(sku, "N/A")
            result_lbl.config(text=f"SKU: {sku}\nAvailable Stock: {stock}")

        search_var.trace_add("write", on_type)
        listbox.bind("<<ListboxSelect>>", on_select)

        search_entry.focus()

    # ================= LOAD JSON =================
    def load_old_data(self):
        files = [f for f in os.listdir(DOWNLOADS) if f.lower().endswith(".json")]
        if not files:
            messagebox.showinfo("Info", "No saved quotations found")
            return

        msg = "Select Quotation:\n\n"
        for i, f in enumerate(files, 1):
            msg += f"{i}. {f}\n"

        choice = simpledialog.askinteger("Load Quotation", msg, minvalue=1, maxvalue=len(files))
        if not choice:
            return

        with open(os.path.join(DOWNLOADS, files[choice-1]), "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict) and "items" in data:
            meta = data.get("meta", {})
            self.items = data.get("items", [])

            self.party.delete(0, tk.END)
            self.party.insert(0, meta.get("party", ""))

            self.phone.delete(0, tk.END)
            self.phone.insert(0, meta.get("phone", ""))
            
            self.sales_person.delete(0, tk.END)
            self.sales_person.insert(0, meta.get("sales_person", ""))
            
            # ---- RATE DISCOUNT (RADIO BUTTON) ----
            saved_rate_disc = meta.get("rate_discount", 0)
            if saved_rate_disc in (55, 57):
                self.rate_discount_var.set(saved_rate_disc)
            else:
                self.rate_discount_var.set(57)   # default

            # ---- SP DISCOUNT ----
            self.sp_discount.delete(0, tk.END)
            saved_sp_disc = meta.get("sp_discount", "")
            if saved_sp_disc not in (None, ""):
                self.sp_discount.insert(0, str(saved_sp_disc))
            
            self.payment_image_path = meta.get("payment_image", "")
            
            # ---- ADDRESS ----
            self.address.delete(0, tk.END)
            self.address.insert(0, meta.get("address", ""))

            # ---- BILL DISCOUNT ----
            self.bill_discount.delete(0, tk.END)
            self.bill_discount.insert(0, meta.get("bill_discount", ""))

            self.bill_disc_type.set(meta.get("bill_discount_type", "AMOUNT"))

            # ---- SHIPPING ----
            self.shipping.delete(0, tk.END)
            self.shipping.insert(0, meta.get("shipping", ""))

            # ---- ADVANCE ----
            self.advance.delete(0, tk.END)
            self.advance.insert(0, meta.get("advance", ""))

            self.update_header()
        else:
            self.items = []
            
        self.update_payment_image_ui()
        self.refresh()

    # ================= SAVE PDF =================
    def save_pdf(self):
        if not self.items:
            return

        today = datetime.now().strftime("%d-%m-%Y")
        base = f"Quotation_{self.party.get().replace(' ','_')}_{today}"
        remark_text = self.remark.get("1.0", "end").strip()
        
        """
        # ===== UPDATE PER-PCS RATE IF DISCOUNT % CHANGED =====
        try:
            new_disc = float(self.discount.get())
        except:
            new_disc = 0

        # ===== UPDATE PER-PCS RATE ONLY FOR AUTO ITEMS =====
        try:
            new_disc = float(self.discount.get())
        except:
            new_disc = 0

        for item in self.items:
            # Skip SAMPLE items
            if "(SAMPLE)" in item["desc"]:
                continue

            # Skip MANUAL rate items
            if item.get("is_manual"):
                continue

            sku = item["desc"].strip()

            if sku in SKU_DB:
                mrp = SKU_DB[sku]["MRP"]
                raw = (mrp * (100 - new_disc)) / 100
                new_rate = int(raw) + (1 if raw - int(raw) >= 0.5 else 0)

                item["rate"] = new_rate
                item["amount"] = item["pcs"] * new_rate
                
                """

                
        try:
            rate_disc = self.rate_discount_var.get()
            try:
                sp_disc = float(self.sp_discount.get())
            except:
                sp_disc = 0
            if rate_disc not in (55, 57):
                rate_disc = 0
        except:
            rate_disc = 0

        try:
            sp_disc = float(self.sp_discount.get())
        except:
            sp_disc = 0

        total_disc = rate_disc + sp_disc

        if sp_disc > 0:
            total_discount_text = f"{rate_disc + sp_disc} %"
        else:
            total_discount_text = f"{rate_disc} %"




        # ---- SAVE JSON ----
        data = {
            "meta": {
                "party": self.party.get(),
                "phone": self.phone.get(),
                "address": self.address.get(),
                "sales_person": self.sales_person.get(),   # 👈 ADD
                "rate_discount": self.rate_discount_var.get(),    # rate discount
                "sp_discount": self.sp_discount.get(),
                "total_discount_text": total_discount_text,
                "bill_discount": self.bill_discount.get(),
                "bill_discount_type": self.bill_disc_type.get(),
                "shipping": self.shipping.get(),
                "advance": self.advance.get(),
                "payment_image": self.payment_image_path,
                "date": today
            },
            "items": self.items
        }


        with open(os.path.join(DOWNLOADS, base + ".json"), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        # ---- PDF ----
        pdf = os.path.join(DOWNLOADS, base + ".pdf")
        doc = SimpleDocTemplate(pdf, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=10 )
        styles = getSampleStyleSheet()
        center = ParagraphStyle("center", parent=styles["Normal"], alignment=TA_CENTER)

        elements = []

        elements.append(Paragraph(
            "<b>ASTRIKE SPORTSWEAR PVT LTD</b>",
            ParagraphStyle("t", parent=styles["Title"], alignment=TA_CENTER)
        ))

        elements.append(Paragraph(
            "Ground Floor B-124 Shop No. 2 Pratap Garden, Uttam Nagar New Delhi<br/>"
            "Phone: 7838000995 | Email: info@astrikesports.com<br/>"
            "GSTIN: 07ABCCA4620J1ZV | State: 07-Delhi",
            center
        ))

        elements.append(Spacer(1, 15))
        elements.append(Paragraph("<b>QUOTATION</b>",
                                  ParagraphStyle("q", parent=styles["Title"], alignment=TA_CENTER)))
        elements.append(Spacer(1, 10))
        
        # ---- CUSTOMER TABLE ----
        details_table = [
            [
                Paragraph("<b>Party Name :</b> " + self.safe(self.party.get()), styles["Normal"]),
                Paragraph("<b>Phone :</b> " + self.safe(self.phone.get()), styles["Normal"]),
                Paragraph("<b>Date :</b> " + today, styles["Normal"]),
            ],
            [
                Paragraph("<b>Sales Person :</b> " + self.safe(self.sales_person.get()), styles["Normal"]),
                Paragraph("<b>Rate Discount :</b> " + f"{rate_disc} %", styles["Normal"]),
                Paragraph(
                    "<b>SP Discount :</b> " + f"{sp_disc} %",
                    styles["Normal"]
                ) if sp_disc > 0 else "",
            ],
            [
                Paragraph("<b>Address :</b> " + self.safe(self.address.get()), styles["Normal"]),
                "", ""
            ],
            [
                Paragraph("<b>Total Discount :</b> " + total_discount_text, styles["Normal"]),
                "", ""
            ],
            [
                Paragraph("<b>Remark :</b> " + remark_text, styles["Normal"]),
                "", ""
            ],
        ]

        
        dt = Table(
        details_table,
        colWidths=[180, 180, 180]   # ✅ 3 equal columns
    )

        dt.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("SPAN", (0,2), (2,2)),   # Address full row
            ("SPAN", (0,3), (2,3)),   # Total Discount full row
            ("SPAN", (0,4), (2,4)),   # Total Discount full row
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ]))

        elements.append(dt)
        elements.append(Spacer(1, 5))


        # ---- ITEM TABLE ----
        table = [[
            "DESC",
            "S", "M", "L", "XL", "2XL", "3XL", "4XL",
            "PCS", "RATE", "AMOUNT", "MRP", "PACKING"
        ]]


        for i in self.items:
            sku = i["desc"].replace(" (SAMPLE)", "").strip()

            mrp = SKU_DB.get(sku, {}).get("MRP", "-")
            packing = SKU_DB.get(sku, {}).get("PCS", "-")

            size_map = self.parse_sizes(i["size"])

            table.append([
                Paragraph(self.safe(sku), styles["Normal"]),
                size_map["S"],
                size_map["M"],
                size_map["L"],
                size_map["XL"],
                size_map["2XL"],
                size_map["3XL"],
                size_map["4XL"],
                str(i["pcs"]),
                f"Rs {i['rate']}",
                f"Rs {i['amount']}",
                str(mrp),
                str(packing)
            ])


        t = Table(
            table,
            colWidths=[
                80,                     # DESC
                30, 30, 30, 30, 30, 30, 30,   # S–4XL
                40,                     # PCS
                55,                     # RATE
                75,                     # AMOUNT
                35, 45                  # MRP PACKING
            ],
            repeatRows=1
        )



        t.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("ALIGN", (1,1), (7,-1), "CENTER"),   # size columns
            ("ALIGN", (8,1), (-1,-1), "CENTER"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))


        elements.append(t)
        elements.append(Spacer(1, 15))
        

        # ---- CALCULATION (SMART SHIPPING) ----
        total_amt = sum(i["amount"] for i in self.items)

        shipping_raw = self.shipping.get().strip()
        if shipping_raw.isdigit():
            shipping_val = int(shipping_raw)
            shipping_display = f"Rs {shipping_val}"
        else:
            shipping_val = 0
            shipping_display = shipping_raw if shipping_raw else "-"

        bill_disc_input = int(self.bill_discount.get()) if self.bill_discount.get().isdigit() else 0

        if self.bill_disc_type.get() == "PERCENT":
            bill_disc_amt = int((total_amt * bill_disc_input) / 100)
            bill_disc_display = f"{bill_disc_input} %"
        else:
            bill_disc_amt = bill_disc_input
            bill_disc_display = f"Rs {bill_disc_amt}"

        advance_val = int(self.advance.get()) if self.advance.get().isdigit() else 0
        net_payable = total_amt + shipping_val - bill_disc_amt - advance_val


        calc_table = [
            ["AMOUNT", f"Rs {total_amt}"],
            ["SHIPPING", shipping_display],
            ["BILL DISCOUNT", bill_disc_display],
            ["ADVANCE", f"Rs {advance_val}"],
            ["NET PAYABLE", f"Rs {net_payable}"],
        ]

        calc = Table(
            calc_table,
            colWidths=[120, 90]   # total = 210
        )

        calc.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
            ("ALIGN", (1,0), (-1,-1), "RIGHT"),

            # 🔥 THIS FIXES LEFT EXTRA SPACE
            ("LEFTPADDING", (0,0), (-1,-1), 4),
            ("RIGHTPADDING", (0,0), (-1,-1), 4),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        
        
        # ---------- RIGHT SIDE FOOTER (DATE / TIME etc.) ----------
        footer_info = Table(
            [
                ["DATE", ""],
                ["TIME", ""],
                ["DIMENSION", ""],
                ["WEIGHT", ""],
                ["SIGN", ""],
            ],
            colWidths=[90, 120]   # total = 210 (calc ke equal)
        )

        footer_info.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 1, colors.black),
            ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))

        right_block = Table(
            [
                [calc],
                [Spacer(1, 8)],
                [footer_info]
            ],
            colWidths=[210]   # EXACT same as calc
        )

        right_block.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))





        # =========================================================
        # CANCEL ITEM FROM BILL (SHOW / HIDE WITHOUT SHIFT)
        # =========================================================

        show_cancel_block = bool(self.payment_image_path)

        # ---------- LEFT BLOCK (CANCEL OR PLACEHOLDER) ----------
        if show_cancel_block:
            # REAL CANCEL TABLE (visible after payment screenshot)
            left_block = Table(
                [
                    ["CANCEL ITEM FROM BILL"],
                    ["SKU", "SIZE", "REMARK"],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""],
                    ["", "", ""],
                ],
                colWidths=[90, 90, 120]   # total = 300
            )

            left_block.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 1, colors.black),
                ("BACKGROUND", (0,0), (-1,0), colors.black),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("SPAN", (0,0), (-1,0)),
                ("ALIGN", (0,0), (-1,0), "CENTER"),
                ("FONTNAME", (0,0), (-1,1), "Helvetica-Bold"),
                ("ALIGN", (0,1), (-1,-1), "CENTER"),
                ("TOPPADDING", (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ]))

        else:
            # BLANK PLACEHOLDER (same width, invisible)
            left_block = Table(
                [[""], [""], [""], [""], [""], [""], [""], [""]],
                colWidths=[90, 90, 120]
            )

            left_block.setStyle(TableStyle([
                ("GRID", (0,0), (-1,-1), 0, colors.white),
            ]))


        # ---------- SIDE BY SIDE (ALWAYS ADD ONCE) ----------
        side_by_side = Table(
            [[left_block, " ", right_block]],
            colWidths=[300, 20, 210]
        )

        side_by_side.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING", (0,0), (-1,-1), 0),
        ]))

        elements.append(Spacer(1, 4))
        elements.append(side_by_side)


        
        
        """""

            # ---------- FOOTER BLOCK (KEEP TOGETHER) ----------
        footer_block = []
        # ---------- DATE / DIMEN / SIGN (BLANK) ----------
        footer_info = Table(
            [[
                "DATE & TIME",
                "DIMEN. & WEIGHT",
                "SIGN"
            ]],
        colWidths=[300, 300, 200]
        )

        footer_info.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ALIGN", (0,0), (0,0), "LEFT"),     # DATE & TIME
            ("ALIGN", (1,0), (1,0), "LEFT"),   # DIMEN & WEIGHT
            ("ALIGN", (2,0), (2,0), "LEFT"),    # SIGN
            ("TOPPADDING", (0,0), (-1,-1), 12),
            ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ]))

        footer_block.append(Spacer(1, 170)) # isse nichee ho jaygea
        footer_block.append(footer_info)

        line = Table(
            [[""]],
            colWidths=[800],   # item table ki total width
            rowHeights=[1]
        )

        line.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.black),
        ]))

        footer_block.append(Spacer(1, 2))
        footer_block.append(line)
        footer_block.append(Spacer(1, 8))

        note_para = Paragraph(
            "<b>IMP. NOTE</b> &nbsp;&nbsp;• Quotation valid for 2 hours only. "
            "• Delivery time 4–5 working days.",
            ParagraphStyle(
                "imp_note",
                fontSize=9,
                leading=12
            )
        )

        footer_block.append(note_para)

        remark_text = self.remark.get("1.0", "end").strip()

        remark_para = Paragraph(
            f"<b>REMARK</b> &nbsp;&nbsp;{self.safe(remark_text) if remark_text else '-'}",
            ParagraphStyle(
                "remark",
                fontSize=9,
                leading=12
            )
        )

        footer_block.append(Spacer(1, 2))
        footer_block.append(remark_para)
        
        footer_frame = KeepInFrame(
        maxWidth=800,     # item table ki total width
        maxHeight=380,     # footer ki approx height
        content=footer_block,
         #mode="shrink"      🔥 ye hi footer ko same page me rakhega
        )
        
        elements.append(footer_frame)

        """""

                        # ===== PAYMENT IMAGE PAGE =====
        if self.payment_image_path and os.path.exists(self.payment_image_path):
            try:
                elements.append(PageBreak())

                elements.append(Paragraph(
                    "<b>PAYMENT DETAILS</b>",
                    ParagraphStyle(
                        "pay_title",
                        parent=styles["Title"],
                        alignment=TA_CENTER
                    )
                ))

                elements.append(Spacer(1, 20))

                img = Image(self.payment_image_path)
                img._restrictSize(400, 550)
                elements.append(img)

            except Exception as e:
                messagebox.showerror(
                    "PDF Image Error",
                    f"Payment image could not be added.\n\n{e}"
                )
                
        
        doc.build(elements)
        messagebox.showinfo("Saved", "PDF & JSON saved in Downloads")

# ================= RUN =================
root = tk.Tk()
QuotationApp(root)
root.mainloop()