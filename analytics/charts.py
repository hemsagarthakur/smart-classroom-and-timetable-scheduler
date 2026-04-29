import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from flask import current_app


def generate_workload_chart(faculty_data, save_path):
    try:
        df = pd.DataFrame(faculty_data)
        if df.empty:
            return None
        colors = ["#198754" if row["scheduled_hours"] <= row["max_hours"] else "#dc3545" for _, row in df.iterrows()]
        plt.figure(figsize=(12, 6))
        plt.bar(df["name"], df["scheduled_hours"], color=colors)
        if "max_hours" in df and not df["max_hours"].empty:
            plt.axhline(df["max_hours"].max(), color="red", linestyle="--", linewidth=1.5, label="Max Hours Limit")
            plt.legend()
        plt.title("Faculty Workload")
        plt.xlabel("Faculty")
        plt.ylabel("Scheduled Hours")
        plt.xticks(rotation=35, ha="right")
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        return save_path
    except Exception as exc:
        current_app.logger.error(f"Chart generation failed: {exc}")
        plt.close()
        return None


def generate_room_utilization_chart(room_data, slot_data, save_path):
    try:
        df = pd.DataFrame(slot_data)
        rooms_df = pd.DataFrame(room_data)
        if df.empty or rooms_df.empty:
            return None
        pivot = df.pivot_table(index="room_code", columns="day", values="period_number", aggfunc="count", fill_value=0)
        pivot = pivot.reindex(rooms_df["room_code"], fill_value=0)
        plt.figure(figsize=(10, 8))
        heatmap = plt.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
        plt.colorbar(heatmap, label="Slots Used")
        plt.xticks(range(len(pivot.columns)), pivot.columns)
        plt.yticks(range(len(pivot.index)), pivot.index)
        plt.title("Room Utilization Heatmap")
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        return save_path
    except Exception as exc:
        current_app.logger.error(f"Chart generation failed: {exc}")
        plt.close()
        return None


def generate_subject_distribution_chart(subject_data, save_path):
    try:
        df = pd.DataFrame(subject_data)
        if df.empty:
            return None
        grouped = df.groupby("department_code").size()
        plt.figure(figsize=(8, 8))
        wedges, _, _ = plt.pie(grouped.values, autopct="%1.1f%%", startangle=90)
        labels = [f"{name} ({count})" for name, count in zip(grouped.index, grouped.values)]
        plt.legend(wedges, labels, title="Departments", loc="center left", bbox_to_anchor=(1, 0.5))
        plt.title("Subject Distribution by Department")
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        return save_path
    except Exception as exc:
        current_app.logger.error(f"Chart generation failed: {exc}")
        plt.close()
        return None
