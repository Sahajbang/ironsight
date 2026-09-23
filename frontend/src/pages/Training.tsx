import { useState } from "react";

import { useBookSlot, useInstructors, useTraining, useTrainingRecommendations } from "../api/client";
import { Badge, Button, Card, CardSkeleton, Empty, Icon, Meter, Tabs, type IconName } from "../design";
import { dayTime, duration } from "../lib/format";
import { useApp } from "../state/store";
import "./pages.css";

const TYPE_ICON: Record<string, IconName> = {
  video: "video",
  handbook: "book",
  checklist: "check",
  instructor: "user",
  simulation: "sim",
};

const TYPE_LABEL: Record<string, string> = {
  video: "eLearning videos",
  handbook: "Handbooks & manuals",
  checklist: "Quick-reference checklists",
  instructor: "Instructor-led",
  simulation: "Simulations",
};

export function Training() {
  const { operatorId } = useApp();
  const { data, isLoading } = useTraining(operatorId);
  const { data: recs } = useTrainingRecommendations(operatorId);
  const { data: slots } = useInstructors();
  const book = useBookSlot();
  const [filter, setFilter] = useState<string>("all");

  const categories = data?.categories ?? [];
  const visible = filter === "all" ? categories : categories.filter((c) => c.content_type === filter);
  const progressPct = data ? (data.progress.completed / Math.max(data.total, 1)) * 100 : 0;

  return (
    <div className="page__grid">
      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card title="Recommended for you" icon="target">
          {/* Each recommendation states the trigger. "Because your last two trenching cycles
              ran long" is actionable; "recommended for you" is not. */}
          <div className="stack" data-guide-id="training-recommendations">
            {!recs && <CardSkeleton rows={3} />}
            {recs?.length === 0 && <Empty icon="check">Nothing outstanding — you are current on training.</Empty>}
            {recs?.map((rec) => (
              <article key={rec.content.id} className="rec">
                <span className="tile__icon">
                  <Icon name={TYPE_ICON[rec.content.content_type] ?? "file"} size={18} />
                </span>
                <div className="col grow" style={{ gap: 4 }}>
                  <div className="row wrap" style={{ gap: 8 }}>
                    <strong className="tile__title">{rec.content.title}</strong>
                    {rec.content.duration_min && <Badge>{duration(rec.content.duration_min)}</Badge>}
                  </div>
                  <span className="rec__why">
                    <Icon name="info" size={12} style={{ display: "inline", verticalAlign: "-2px" }} /> {rec.reason}
                  </span>
                  <p className="tile__text">{rec.content.body_text}</p>
                </div>
              </article>
            ))}
          </div>
        </Card>

        <Card
          title="Training catalogue"
          icon="book"
          action={
            <Tabs
              value={filter}
              onChange={setFilter}
              options={[
                { value: "all", label: "All" },
                { value: "video", label: "Video" },
                { value: "handbook", label: "Manuals" },
                { value: "simulation", label: "Sim" },
                { value: "instructor", label: "Instructor" },
              ]}
            />
          }
        >
          <div className="col" style={{ gap: "var(--s5)" }} data-guide-id="open-training">
            {isLoading && <CardSkeleton rows={5} />}
            {visible.map((cat) => (
              <div key={cat.content_type} className="col" style={{ gap: "var(--s3)" }}>
                <span className="label">{TYPE_LABEL[cat.content_type] ?? cat.content_type}</span>
                <div className="tgrid">
                  {cat.items.map((item) => (
                    <article key={item.id} className="tile">
                      <div className="row" style={{ justifyContent: "space-between" }}>
                        <span className="tile__icon">
                          <Icon name={TYPE_ICON[item.content_type] ?? "file"} size={18} />
                        </span>
                        {item.status === "Completed" ? (
                          <Badge tone="ok">Done</Badge>
                        ) : item.status === "In Progress" ? (
                          <Badge tone="accent">Started</Badge>
                        ) : null}
                      </div>
                      <strong className="tile__title">{item.title}</strong>
                      <p className="tile__text">{item.body_text}</p>
                      <div className="row" style={{ justifyContent: "space-between", marginTop: "auto" }}>
                        <span className="muted" style={{ fontSize: "0.72rem" }}>
                          {item.machine_family}
                          {item.duration_min ? ` · ${duration(item.duration_min)}` : ""}
                        </span>
                        <Icon name="chevronRight" size={15} style={{ color: "var(--text-muted)" }} />
                      </div>
                    </article>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="col" style={{ gap: "var(--s5)" }}>
        <Card title="Your progress" icon="chart">
          {data && (
            <div className="col" style={{ gap: "var(--s3)" }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <span className="stat__value">{data.progress.completed}</span>
                <span className="muted" style={{ fontSize: "0.8rem" }}>of {data.total} completed</span>
              </div>
              <Meter value={progressPct} tone="ok" />
              <div className="sumgrid">
                <div className="col" style={{ gap: 1 }}>
                  <span className="label">In progress</span>
                  <strong>{data.progress.in_progress}</strong>
                </div>
                <div className="col" style={{ gap: 1 }}>
                  <span className="label">Not started</span>
                  <strong>{data.progress.not_started}</strong>
                </div>
              </div>
            </div>
          )}
        </Card>

        <Card title="Book an instructor" icon="calendar">
          <div className="stack" data-guide-id="book-instructor">
            {!slots && <CardSkeleton rows={3} />}
            {slots?.length === 0 && <Empty icon="calendar">No upcoming sessions.</Empty>}
            {slots?.slice(0, 6).map((slot) => (
              <div key={slot.id} className="slot">
                <span className="col grow" style={{ gap: 1 }}>
                  <strong style={{ fontSize: "0.85rem" }}>{slot.topic}</strong>
                  <span className="muted" style={{ fontSize: "0.72rem" }}>
                    {slot.instructor_name} · {slot.mode}
                    {slot.location ? ` · ${slot.location}` : ""}
                  </span>
                  <span className="muted" style={{ fontSize: "0.72rem" }}>{dayTime(slot.start_time)}</span>
                </span>
                {slot.booked ? (
                  <Badge tone={slot.booked_by_operator_id === operatorId ? "ok" : "neutral"}>
                    {slot.booked_by_operator_id === operatorId ? "Yours" : "Booked"}
                  </Badge>
                ) : (
                  <Button
                    size="sm"
                    disabled={book.isPending}
                    onClick={() => book.mutate({ slotId: slot.id, operatorId })}
                  >
                    Book
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
