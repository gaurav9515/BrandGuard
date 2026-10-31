import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../config/api';
import { useAuth } from './AuthContext';

const CompanyContext = createContext(null);

export function CompanyProvider({ children }) {
  const { user, token } = useAuth();
  const [companies, setCompanies] = useState([]);
  const [activeCompany, setActiveCompany] = useState(null);
  const [projects, setProjects] = useState([]);
  const [activeProject, setActiveProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Load companies for authenticated user
  const fetchCompanies = useCallback(async () => {
    if (!token) {
      setCompanies([]);
      setActiveCompany(null);
      setProjects([]);
      setActiveProject(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/companies/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!res.ok) throw new Error('Failed to load companies');
      const data = await res.json();
      const compList = data.companies || [];
      setCompanies(compList);

      if (compList.length > 0) {
        // Retrieve persisted active company or default to first
        const savedCompId = localStorage.getItem('bg_active_company_id');
        const matched = compList.find(c => c.id === savedCompId);
        const selected = matched || compList[0];
        setActiveCompany(selected);
        localStorage.setItem('bg_active_company_id', selected.id);
      }
    } catch (err) {
      console.warn('Company loading error:', err);
      // Fallback default for demo persona
      const fallbackCompany = {
        id: user?.company_id || 'novapay-default-id',
        name: user?.company_name || 'NovaPay',
        slug: 'novapay',
        ruleset_version: 'v3.2',
        allowed_hex_palette: [
          { name: 'Midnight Emerald', hex: '#0A3423', max_delta_e: 4.0 },
          { name: 'Teal', hex: '#00D4B6', max_delta_e: 4.5 },
          { name: 'Pure White', hex: '#FFFFFF', max_delta_e: 2.0 },
          { name: 'Muted Panel', hex: '#F8FAF9', max_delta_e: 2.0 }
        ],
        allowed_fonts: ['Inter', 'JetBrains Mono', 'Plus Jakarta Sans'],
        wcag_min_ratio: 4.5,
        logo_aspect_ratio: 3.5
      };
      setCompanies([fallbackCompany]);
      setActiveCompany(fallbackCompany);
    } finally {
      setLoading(false);
    }
  }, [token, user?.company_id, user?.company_name]);

  useEffect(() => {
    fetchCompanies();
  }, [fetchCompanies]);

  // Load projects whenever activeCompany changes
  const fetchProjects = useCallback(async (companyId) => {
    if (!token || !companyId) return;

    try {
      const res = await fetch(`${API_BASE}/api/companies/${companyId}/projects/`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'X-Company-ID': companyId
        }
      });
      if (res.ok) {
        const data = await res.json();
        const projList = data.projects || [];
        setProjects(projList);

        if (projList.length > 0) {
          const savedProjId = localStorage.getItem('bg_active_project_id');
          const matched = projList.find(p => p.id === savedProjId);
          const selected = matched || projList[0];
          setActiveProject(selected);
          localStorage.setItem('bg_active_project_id', selected.id);
        } else {
          setActiveProject(null);
        }
      }
    } catch (err) {
      console.warn('Projects loading error:', err);
      const defaultProj = {
        id: 'default-proj-id',
        name: 'Global Launch Campaign',
        slug: 'global-launch-campaign',
        channel: 'ALL'
      };
      setProjects([defaultProj]);
      setActiveProject(defaultProj);
    }
  }, [token]);

  useEffect(() => {
    if (activeCompany?.id) {
      fetchProjects(activeCompany.id);
    }
  }, [activeCompany?.id, fetchProjects]);

  const switchCompany = (companyId) => {
    const found = companies.find(c => c.id === companyId);
    if (found) {
      setActiveCompany(found);
      localStorage.setItem('bg_active_company_id', found.id);
    }
  };

  const switchProject = (projectId) => {
    const found = projects.find(p => p.id === projectId);
    if (found) {
      setActiveProject(found);
      localStorage.setItem('bg_active_project_id', found.id);
    }
  };

  const createCompany = async (companyData) => {
    if (!token) throw new Error('Authentication required');
    const res = await fetch(`${API_BASE}/api/companies/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(companyData)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to create company');
    await fetchCompanies();
    if (data.company) {
      switchCompany(data.company.id);
    }
    return data.company;
  };

  const createProject = async (projectData) => {
    if (!token || !activeCompany) throw new Error('Active company required');
    const res = await fetch(`${API_BASE}/api/companies/${activeCompany.id}/projects/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'X-Company-ID': activeCompany.id
      },
      body: JSON.stringify(projectData)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Failed to create project');
    await fetchProjects(activeCompany.id);
    if (data.project) {
      switchProject(data.project.id);
    }
    return data.project;
  };

  return (
    <CompanyContext.Provider
      value={{
        companies,
        activeCompany,
        projects,
        activeProject,
        loading,
        error,
        switchCompany,
        switchProject,
        fetchCompanies,
        createCompany,
        createProject
      }}
    >
      {children}
    </CompanyContext.Provider>
  );
}

export function useCompany() {
  const context = useContext(CompanyContext);
  if (!context) {
    throw new Error('useCompany must be used within a CompanyProvider');
  }
  return context;
}

