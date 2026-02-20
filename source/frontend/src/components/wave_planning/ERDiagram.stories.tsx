/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import React from "react";
import type { Meta, StoryObj } from "@storybook/react";

import ERDiagram, { ERDiagramProps } from "./ERDiagram";
import {
  sampleApplications,
  sampleDatabases,
  sampleMoveGroups,
  sampleServers,
  sampleWaves,
  wpmSchemas,
} from "../../../test_data";
import { Container } from "@cloudscape-design/components";

const meta: Meta<typeof ERDiagram> = {
  title: "ER Diagram",
  component: ERDiagram,
  parameters: {
    layout: "none",
  },
  tags: ["autodocs"],
};

export default meta;

type Story = StoryObj<typeof meta>;

// A container that simulates a flex display with the component displayed in bottom row
const StoryWrapper = (props: ERDiagramProps) => {
  // Keep track of slow renders
  const slowRenders = React.useRef<{
    warnings: number;
    errors: number;
  }>({
    warnings: 0,
    errors: 0,
  });

  const onRenderCallback: React.ProfilerOnRenderCallback = (id, phase, actualDuration) => {
    // Round to 2 decimal places
    const warningThreshold = 16; // one frame
    const errorThreshold = 50;
    const duration = Math.round(actualDuration * 100) / 100;

    // Create a meaningful message
    const message = {
      component: id,
      phase,
      duration: `${duration}ms`,
      ...(phase === "mount" ? { message: "Initial render" } : { message: "Re-render" }),
    };

    // Log based on severity
    if (duration > errorThreshold) {
      slowRenders.current.errors++;
      console.error("🔴 Very slow render:", {
        ...message,
        slowRenderCount: slowRenders.current.errors,
      });
    } else if (duration > warningThreshold) {
      slowRenders.current.warnings++;
      console.warn("🟡 Slow render:", {
        ...message,
        slowRenderCount: slowRenders.current.warnings,
      });
    } else {
      console.log("🟢 Normal render:", message);
    }

    // Log cumulative stats periodically
    if (slowRenders.current.warnings > 0 || slowRenders.current.errors > 0) {
      console.log("📊 Performance Summary:", {
        component: id,
        warnings: slowRenders.current.warnings,
        errors: slowRenders.current.errors,
        averageRenderTime: duration,
      });
    }
  };

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <div style={{ flex: 30, backgroundColor: "#eee", padding: "10px", alignContent: "center", textAlign: "center" }}>
        Refer to the console to see the React Profiler output
      </div>
      <div style={{ flex: 70, padding: "10px" }}>
        <Container fitHeight disableContentPaddings>
          <React.Profiler id="ERDiagram" onRender={onRenderCallback}>
            <ERDiagram {...props} />
          </React.Profiler>
        </Container>
      </div>
    </div>
  );
};

const schemas = wpmSchemas();
const applications = sampleApplications();
const databases = sampleDatabases();
const servers = sampleServers();
const moveGroups = sampleMoveGroups();
const waves = sampleWaves();

export const Loading: Story = {
  render: () => (
    <StoryWrapper
      {...{
        isLoading: true,
        schemas,
        applications,
        databases,
        servers,
        moveGroups,
        waves,
      }}
    />
  ),
};

export const Waves: Story = {
  render: () => (
    <StoryWrapper
      {...{
        schemas,
        applications,
        databases,
        servers,
        moveGroups,
        waves,
      }}
    />
  ),
};

export const SelectedWaves: Story = {
  render: () => (
    <StoryWrapper
      {...{
        schemas,
        applications,
        databases,
        servers,
        moveGroups,
        waves,
        selectedWaves: waves.filter((w) => w.wave_id === "wave-1"),
      }}
    />
  ),
};

export const MoveGroups: Story = {
  render: () => (
    <StoryWrapper
      {...{
        schemas,
        applications,
        databases,
        servers,
        moveGroups,
      }}
    />
  ),
};

export const SelectedMoveGroups: Story = {
  render: () => (
    <StoryWrapper
      {...{
        schemas,
        applications,
        databases,
        servers,
        moveGroups,
        selectedMoveGroups: moveGroups.filter((mg) => mg.move_group_id === "mg-hrs"),
      }}
    />
  ),
};

export const Applications: Story = {
  render: () => (
    <StoryWrapper
      {...{
        schemas,
        applications,
        databases,
        servers,
      }}
    />
  ),
};
